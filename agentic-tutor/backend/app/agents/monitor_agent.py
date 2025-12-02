# backend/app/agents/monitor_agent.py
import asyncio
import math
from typing import Dict, Any, Optional
from backend.app.agents.base_agent import BaseAgent
from backend.app.core.llm_client import LLMClient
from backend.app.database.session import get_session
from backend.app.database.models import StudentProfile, Event
from datetime import datetime, timezone
from pathlib import Path
import json

PROMPT_PATH = Path(__file__).resolve().parent / "agent_prompts" / "monitor_prompt.txt"

def _compute_risk_score(recent_scores: list, confidence_gap: float = 0.0) -> float:
    """
    Compute a risk score in [0,1]. Higher means more risk.
    Simple heuristic: combination of recent decline & confidence_gap.
    recent_scores: most recent N overall scores (0..1)
    """
    if not recent_scores:
        return 0.0
    # trend: negative if scores declining
    n = len(recent_scores)
    # normalized volatility/trend
    mean = sum(recent_scores) / n
    # slope approx: last - mean
    slope = recent_scores[-1] - mean
    # volatility
    var = sum((s - mean) ** 2 for s in recent_scores) / n
    vol = math.sqrt(var)
    # risk components: low current performance, negative slope, high vol, big confidence gap
    current_risk = max(0.0, (0.5 - recent_scores[-1])) * 2.0  # maps 0.5->1.0 risk when low
    slope_risk = max(0.0, -slope) * 2.0
    vol_risk = min(1.0, vol * 2.0)
    conf_risk = min(1.0, abs(confidence_gap))
    combined = 0.5 * current_risk + 0.2 * slope_risk + 0.2 * vol_risk + 0.1 * conf_risk
    return min(1.0, combined)

class MonitorAgent(BaseAgent):
    def __init__(self, name: str = "monitor", model: str = "openai/gpt-oss-20b"):
        super().__init__(name)
        # LLMClient optional: used to write nicer remediation text
        self.llm = LLMClient(model=model) 
        self.template = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else None

    async def _generate_remediation_with_llm(self, payload: Dict[str,Any]) -> Dict[str,Any]:
        """
        Ask LLM to produce a short remediation plan using the prompt template.
        If LLM unavailable/fails, fallback to rule-based remediation.
        """
        try:
            system_prompt = self.template or "System: produce remediation plan."
            user_prompt = json.dumps(payload, ensure_ascii=False)
            raw = await self.llm.chat(system_prompt=system_prompt, user_prompt=user_prompt)
            # raw should be JSON (enforced by template)
            out = json.loads(raw)
            return out
        except Exception:
            return {}

    async def run(self, goal: str, context: Dict[str,Any]) -> Dict[str,Any]:
        """
        goal: 'decide'
        context.goal_params: { 'student_id', 'profile_snapshot', 'grading' }
        """
        gp = context.get("goal_params") or {}
        student_id = gp.get("student_id")
        profile_snapshot = gp.get("profile_snapshot", {})  # optional
        grading = gp.get("grading", {})  # expected: { 'overall_score': float, 'misconceptions': [...], 'confidence_gap': float? }
        if grading is None or not isinstance(grading, dict):
            grading = {
                "overall_score": 0.0,
                "misconceptions": [],
                "confidence_gap": 0.0,
                "grading": {},  # per-question breakdown placeholder
                "error": "LLM grading failed or returned invalid format"
            }
        policy = gp.get("policy", {"mastery_threshold": 0.8, "consec_required": 2, "escalate_threshold": 0.4})

        overall = float(grading.get("overall_score", 0.0))
        misconceptions = grading.get("misconceptions", []) or []
        confidence_gap = float(grading.get("confidence_gap", 0.0)) if grading.get("confidence_gap") is not None else 0.0

        # load long-term profile if not provided
        session = get_session()
        profile = None
        try:
            profile = session.get(StudentProfile, student_id)
        except Exception:
            profile = None

        # recent scores: read from profile.history if present
        recent_scores = []
        if profile and isinstance(profile.history, list):
            # extract last upto 5 eval overall scores from history items
            for ev in reversed(profile.history):
                if isinstance(ev, dict) and ev.get("type") == "eval_completed":
                    payload = ev.get("payload", {})
                    score = payload.get("score")
                    if isinstance(score, (int, float)):
                        recent_scores.append(float(score))
                    if len(recent_scores) >= 5:
                        return {
                                "next_action": "advance",   # force exit
                                "decision": {
                                    "allow_advance": True,
                                    "remediation_plan": None,
                                    "escalate": False,
                                    "notes": "Insufficient data to make decision."
                                }
                            }
            recent_scores = list(reversed(recent_scores))
        # append current score for risk calc
        recent_scores.append(overall)

        # compute risk
        risk_score = _compute_risk_score(recent_scores, confidence_gap=confidence_gap)

        # decision rules
        allow = False
        escalate = False
        remediation_plan = None

        # rule: pass if overall >= mastery_threshold
        if overall >= policy.get("mastery_threshold", 0.8):
            # check consecutive requirement
            consec_req = int(policy.get("consec_required", 2))
            # count last consec scores >= threshold
            consec = 0
            # include current
            for s in reversed(recent_scores):
                if s >= policy.get("mastery_threshold", 0.8):
                    consec += 1
                else:
                    break
            if consec >= consec_req:
                allow = True
            else:
                allow = False
        else:
            allow = False

        # escalation rules
        if overall < policy.get("escalate_threshold", 0.4):
            escalate = True
        if risk_score > 0.85:
            escalate = True

        # If not allowed, create remediation plan (prefer LLM-generated)
        if not allow:
            # base payload to LLM
            llm_payload = {
                "student_id": str(student_id),
                "profile_snapshot": {
                    "mastery_map": profile.mastery_map if profile else {},
                    "history": profile.history if profile else []
                },
                "eval_summary": {
                    "overall_score": overall,
                    "per_question": grading.get("grading", {}),
                    "misconceptions": misconceptions,
                    "confidence_gap": confidence_gap
                },
                "policy": policy
            }
            plan = {}
            if self.llm and self.template:
                try:
                    plan = await asyncio.wait_for(self._generate_remediation_with_llm(llm_payload), timeout=8.0)
                except Exception:
                    plan = {}
            # fallback: rule-based plan
            if not plan:
                plan = {
                    "allow_advance": False,
                    "remediation_plan": {
                        "action": "remedial",
                        "steps": [
                            "Revise the core definition and relationships for the topic (read a focused summary).",
                            "Work through 3 targeted practice problems with step annotations.",
                            "Attempt a multi-representation exercise (algebraic + geometric) and check intermediate steps."
                        ],
                        "recommended_tutor_mode": "revision"
                    },
                    "escalate": escalate,
                    "notes_for_teacher": "Student shows weakness in the topic; recommend human review if no improvement after remediation."
                }
            remediation_plan = plan.get("remediation_plan") or plan.get("remediation") or plan

        # update profile: mastery_map and history
        if profile is None:
            # create a new profile if student missing
            profile = StudentProfile(student_id=student_id, mastery_map={}, history=[])
            session.add(profile)
            session.commit()
            session.refresh(profile)

        # update mastery map: naive update = max(previous, overall)
        topic_key = gp.get("topic", gp.get("grading_topic", "unknown"))
        if topic_key:
            try:
                current_val = float(profile.mastery_map.get(topic_key, 0.0))
            except Exception:
                current_val = 0.0
            # use exponential smoothing: new = 0.6*prev + 0.4*overall
            new_val = round(max(current_val, 0.6 * current_val + 0.4 * overall), 3)
            profile.mastery_map[topic_key] = new_val

        # append event to history
        hist_item = {
            "type": "eval_completed",
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": {"score": overall, "topic": topic_key}
        }
        profile.history = (profile.history or []) + [hist_item]
        profile.risk_score = round(risk_score, 3)
        profile.last_updated = datetime.now(timezone.utc)
        session.add(profile)

        # add an Audit event
        ev = Event(student_id=student_id, event_type="monitor_decision", payload={
            "allow_advance": allow,
            "remediation_plan": remediation_plan,
            "escalate": escalate,
            "notes": ""
        })
        session.add(ev)
        session.commit()
        session.refresh(profile)

        # Format final decision
        final_decision = {
            "allow_advance": allow,
            "remediation_plan": remediation_plan,
            "escalate": escalate,
            "notes": plan.get("notes_for_teacher") if isinstance(plan, dict) else ""
        }
        return final_decision