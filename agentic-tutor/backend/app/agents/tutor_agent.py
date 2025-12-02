# backend/app/agents/tutor_agent.py
import json
from typing import Dict, Any
from backend.app.agents.base_agent import BaseAgent
from backend.app.core.llm_client import LLMClient
from pathlib import Path
import asyncio

PROMPT_PATH = Path(__file__).resolve().parent / "agent_prompts" / "tutor_prompt.txt"

class TutorAgent(BaseAgent):
    """
    Tutor Agent that uses an LLM to produce a lesson plan.
    It reads the prompt template from agents/agent_prompts/tutor_prompt.txt,
    fills it with the context, and asks the LLM for a JSON response.
    """

    def __init__(self, name: str = "tutor", model: str = "openai/gpt-oss-20b"):
        super().__init__(name)
        self.llm = LLMClient(model=model)
        # Load template once
        if PROMPT_PATH.exists():
            self.template = PROMPT_PATH.read_text(encoding="utf-8")
        else:
            # fallback minimal template
            self.template = "System: You are Tutor Agent. Goal: {goal} Context: {context}"

    async def run(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles goals:
         - teach_topic: expects goal_params with topic, student_id, target_mastery, student_profile
         - provide_hint: expects goal_params with question text
        """
        gp = context.get("goal_params") or {}
        if goal == "teach_topic":
            topic = gp.get("topic", "unknown_topic")
            target_mastery = gp.get("target_mastery", 0.8)
            student_id = context.get("context", {}).get("student_id") or gp.get("student_id")
            student_profile = context.get("context", {}).get("student_profile") or gp.get("student_profile", {})

            # Prepare the user prompt JSON body to fill template
            # user_input = json.dumps({
            #     "student_id": str(student_id),
            #     "topic": topic,
            #     "student_profile": student_profile,
            #     "target_mastery": target_mastery,
            #     "constraints": gp.get("constraints", {"max_lesson_minutes": 15})
            # }, ensure_ascii=False)

            # Use the template as "system" content and the user_input as "user" content
            # If the template contains placeholders, we keep as-is and instruct model to read user_input
            payload = {
                    "student_id": student_id,
                    "topic": topic,
                    "student_profile": student_profile,
                    "target_mastery": target_mastery,
                    "constraints": gp.get("constraints", {"max_lesson_minutes": 15}),
                }
            if gp.get("embedded_context"):
                payload["embedded_context"] = gp["embedded_context"]

            user_input = json.dumps(payload)
            system_prompt = self.template
            user_prompt = f"Input JSON:\n{user_input}\n\nReturn the required JSON ONLY."


            # Call LLM
            raw = await self.llm.chat(system_prompt=system_prompt, user_prompt=user_prompt)

            # Try to parse JSON from LLM output. Models sometimes wrap with backticks or text; we attempt robust parsing.
            plan_json = None
            errors = None
            try:
                # Attempt direct parse
                plan_json = json.loads(raw)
            except Exception:
                # Try to extract JSON substring
                import re
                match = re.search(r"\\{[\\s\\S]*\\}", raw)
                if match:
                    try:
                        plan_json = json.loads(match.group(0))
                    except Exception as e:
                        errors = f"Failed JSON parse after extraction: {e}; raw_output={raw[:400]}"
                else:
                    errors = f"No JSON found in model output. raw_output={raw[:400]}"

            if plan_json is None:
                # Return an informative error-like structure so the orchestrator can decide fallback
                return {"error": "could_not_parse_llm_output", "llm_raw": raw, "parse_error": errors}

            # Success: return the plan

            if not isinstance(plan_json, dict):
                # If the LLM returned a list, string, number, etc., convert to a safe structure
                plan_json = {
                    "plan": plan_json if isinstance(plan_json, list) else [],
                    "expected_metrics": {},
                    "metadata": {},
                    "error": "LLM returned non-dict JSON"
                }
            return {"plan": plan_json.get("plan", []), "expected_metrics": plan_json.get("expected_metrics", {}), "metadata": plan_json.get("metadata", {})}

        elif goal == "provide_hint":
            qtext = gp.get("question", "")
            system_prompt = "System: You are a Tutor Agent. Provide a short hint (no full solution) for the question."
            user_prompt = f"Question: {qtext}\nReturn JSON: {{'hint':'<text>'}}"
            raw = await self.llm.chat(system_prompt=system_prompt, user_prompt=user_prompt)
            # Try parse
            try:
                parsed = json.loads(raw)
                return {"hint": parsed.get("hint")}
            except Exception:
                return {"hint_raw": raw}
        else:
            raise ValueError(f"TutorAgent cannot handle goal {goal}")
