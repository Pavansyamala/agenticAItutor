# backend/app/core/orchestrator.py
from typing import TypedDict, Annotated, Literal, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from backend.app.agents.tutor_agent import TutorAgent
from backend.app.agents.evaluator_agent import EvaluatorAgent
from backend.app.agents.monitor_agent import MonitorAgent
from backend.app.database.session import get_session
from backend.app.database.models import Event, StudentProfile
from langgraph.checkpoint.memory import MemorySaver
from backend.app.core.rag.rag_service import RAGService

import uuid
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio

# === RATE LIMITER IMPORT ===
from backend.app.utils.rate_limiter import with_rate_limit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_event(student_id: str, event_type: str, payload: dict, thread_id: str = None):
    try:
        with get_session() as session:
            event = Event(
                event_id=uuid.uuid4().hex,
                student_id=student_id,
                event_type=event_type,
                payload={**payload, "thread_id": thread_id or "unknown"},
                created_at=datetime.utcnow()
            )
            session.add(event)
            session.commit()
    except Exception as e:
        logger.warning(f"Failed to log event: {e}")

class RateLimitError(Exception): pass
class APIError(Exception): pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, APIError, ConnectionError, TimeoutError)),
)
async def call_agent_with_retry(agent, goal: str, context: dict):
    try:
        result = await agent.run(goal, context)
        if isinstance(result, dict) and any(kw in str(result).lower() for kw in ["rate limit", "429"]):
            raise RateLimitError("Rate limit detected")
            logger.warning(f"{agent.name} error: {result['error']} – Using fallback")
        return result
    except Exception as e:
        if any(kw in str(e).lower() for kw in ["429", "rate limit"]):
            raise RateLimitError(str(e))
        elif "timeout" in str(e).lower():
            raise APIError(str(e))
        else:
            logger.error(f"Agent {agent.__class__.__name__} failed: {e}")
            return get_fallback_response(agent.__class__.__name__, goal)

def get_fallback_response(agent_name: str, goal: str) -> Dict[str, Any]:
    fallbacks = {
        "TutorAgent": {"plan": [{"title": "Core Review", "content": "Please review your notes on this topic."}], "metadata": {"fallback": True}},
        "EvaluatorAgent": {"questions": [{"qid": "fb1", "prompt": "Explain the main concept.", "rubric": {"full_marks": 10}}]} if goal == "generate_questions" else {"overall_score": 0.6, "misconceptions": ["Using fallback grading"]},
        "MonitorAgent": {"allow_advance": False, "remediation_plan": {"action": "review", "steps": ["Re-read lesson"]}} }
    return fallbacks.get(agent_name, fallbacks["MonitorAgent"])

# =================================================================
# 1. Shared State
# =================================================================
class AgentState(TypedDict):
    student_id: str
    topic: str
    thread_id: str
    lesson_only: bool

    lesson_plan: Optional[List[Dict[str, Any]]]
    tutor_messages: Annotated[List[Dict], "append"]

    questions: Optional[List[Dict[str, Any]]]
    student_answers: Optional[List[Dict[str, Any]]]
    grading_result: Optional[Dict[str, Any]]

    monitor_decision: Optional[Dict[str, Any]]
    allow_advance: bool
    remediation_plan: Optional[Dict[str, Any]]

    rag_context: str
    messages: Annotated[List[Dict[str, str]], "append"]
    profile_snapshot: Optional[Dict[str, Any]]


# =================================================================
# 2. Orchestrator
# =================================================================
class Orchestrator:
    def __init__(self):
        self.tutor = TutorAgent()
        self.evaluator = EvaluatorAgent()
        self.monitor = MonitorAgent()

        asyncio.create_task(self._init_rag())
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    async def _init_rag(self):
        try:
            await asyncio.to_thread(RAGService.initialize)
            logger.info("RAG Service initialized")
        except Exception as e:
            logger.error(f"RAG init failed: {e}")

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("tutor", self.tutor_node)
        workflow.add_node("generate_questions", self.generate_questions_node)
        workflow.add_node("grade_answers", self.grade_answers_node)
        workflow.add_node("monitor", self.monitor_node)

        workflow.set_entry_point("tutor")

        workflow.add_conditional_edges(
            "tutor",
            lambda state: END if state.get("lesson_only", False) else "generate_questions",
            {END: END, "generate_questions": "generate_questions"}
        )

        workflow.add_edge("generate_questions", "grade_answers")
        workflow.add_edge("grade_answers", "monitor")

        workflow.add_conditional_edges(
            "monitor",
            self._route_after_monitor,
            {"advance": END, "teach": "tutor", "remediate": "tutor", "evaluate": "generate_questions"}
        )

        return workflow.compile(checkpointer=self.memory)

    # =================================================================
    # RATE-LIMITED AGENT CALLS
    # =================================================================
    @with_rate_limit
    async def _call_tutor(self, context: dict):
        return await call_agent_with_retry(self.tutor, "teach_topic", context)

    @with_rate_limit
    async def _call_evaluator(self, goal: str, context: dict):
        return await call_agent_with_retry(self.evaluator, goal, context)

    @with_rate_limit
    async def _call_monitor(self, context: dict):
        return await call_agent_with_retry(self.monitor, "decide", context)

    # =================================================================
    # Nodes
    # =================================================================
    async def tutor_node(self, state: AgentState) -> Dict[str, Any]:
        profile = state.get("profile_snapshot") or await self._get_profile(state["student_id"])
        rag_context = RAGService.get_context(f"explain {state['topic']} with examples", use_tavily=False)

        result = await self._call_tutor({
            "goal_params": {
                "topic": state["topic"],
                "student_profile": profile,
                "embedded_context": rag_context
            }
        })

        log_event(state["student_id"], "lesson_delivered", {"topic": state["topic"]}, state["thread_id"])   

        return {
            "lesson_plan": result.get("plan"),
            "tutor_messages": [{"role": "tutor", "content": "Lesson ready"}],
            "rag_context": rag_context,
            "profile_snapshot": profile,
            "messages": [{"role": "system", "content": f"Taught {state['topic']}"}]
        }

    async def generate_questions_node(self, state: AgentState) -> Dict[str, Any]:
        rag_context = RAGService.get_context(state["topic"], use_tavily=False)

        result = await self._call_evaluator("generate_questions", {
            "goal_params": {
                "topic": state["topic"],
                "embedded_context": rag_context
            }
        })

        questions = result.get("questions", [])[:3] or [
            {"qid": "fb1", "prompt": f"Explain {state['topic']} in your own words.", "type": "conceptual"}
        ]

        log_event(state["student_id"], "questions_generated", {"count": len(questions)}, state["thread_id"])

        return {
            "questions": questions,
            "rag_context": rag_context,
            "messages": [{"role": "evaluator", "content": f"{len(questions)} questions generated"}]
        }

    async def grade_answers_node(self, state: AgentState) -> Dict[str, Any]:
        if not state.get("student_answers"):
            return {"grading_result": {"overall_score": 0.0}}

        result = await self._call_evaluator("grade_answers", {
            "goal_params": {
                "eval_record": {"questions": state["questions"]},
                "student_answers": state["student_answers"]
            }
        })

        log_event(state["student_id"], "answers_graded", {"score": result.get("overall_score", 0)}, state["thread_id"])
        return {"grading_result": result}

    async def monitor_node(self, state: AgentState) -> Dict[str, Any]:
        grading = state.get("grading_result") or {}
        score = grading.get("overall_score", 0.0)
        profile = state.get("profile_snapshot") or await self._get_profile(state["student_id"])

        result = await self._call_monitor({
            "goal_params": {
                "eval_summary": {"overall_score": score, "misconceptions": grading.get("misconceptions", [])},
                "profile_snapshot": profile
            }
        }) or {"allow_advance": score >= 0.8}

        allow_advance = bool(result.get("allow_advance", False))
        remediation = result.get("remediation_plan", {})
        action = remediation.get("action", "review") if isinstance(remediation, dict) else "review"
        next_route = "advance" if allow_advance else {"practice": "evaluate", "remedial": "remediate"}.get(action, "teach")

        log_event(state["student_id"], "monitor_decision", {"allow_advance": allow_advance}, state["thread_id"])

        return {
            "monitor_decision": result,
            "allow_advance": allow_advance,
            "remediation_plan": remediation,
            "messages": [{"role": "monitor", "content": f"Decision: {next_route}"}]
        }

    def _route_after_monitor(self, state: AgentState) -> str:
        if state.get("allow_advance"):
            return "advance"
        action = (state.get("monitor_decision") or {}).get("remediation_plan", {}).get("action", "review")
        return {"practice": "evaluate", "remedial": "remediate"}.get(action, "teach")

    async def _get_profile(self, student_id: str) -> dict:
        try:
            with get_session() as session:
                profile = session.query(StudentProfile).filter(StudentProfile.student_id == student_id).first()
                if not profile:
                    return {"student_id": student_id, "mastery_map": {}, "misconceptions": []}
                return {
                    "student_id": profile.student_id,
                    "mastery_map": profile.mastery_map or {},
                    "misconceptions": profile.misconceptions or [],
                    "overall_score": profile.overall_score or 0.0,
                    "learning_preferences": profile.learning_preferences or {}
                }
        except Exception as e:
            logger.warning(f"Profile error: {e}")
            return {"student_id": student_id, "mastery_map": {}, "misconceptions": []}

    # =================================================================
    # Public API
    # =================================================================
    async def start_session(self, student_id: str, topic: str) -> dict:
        thread_id = f"{student_id}_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "student_id": student_id, "topic": topic, "thread_id": thread_id,
            "lesson_only": True, "student_answers": [], "questions": [], "messages": [],
            "profile_snapshot": await self._get_profile(student_id)
        }

        log_event(student_id, "session_started", {"topic": topic}, thread_id)
        result = await self.graph.ainvoke(initial_state, config)

        return {"thread_id": thread_id, "lesson_plan": result.get("lesson_plan"), "status": "lesson_ready"}

    async def submit_answers(self, thread_id: str, answers: List[Dict]) -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        if not snapshot or not snapshot.values:
            return {"status": "error", "error": "Session not found"}

        current = snapshot.values.copy()
        current.update({"student_answers": answers, "lesson_only": False})

        final_state = await self.graph.ainvoke(current, config)

        return {
            "status": "success",
            "questions": final_state.get("questions"),
            "grading": final_state.get("grading_result"),
            "decision": final_state.get("monitor_decision"),
            "next_action": "advance" if final_state.get("allow_advance") else "continue"
        }

    def get_state(self, thread_id: str):
        state = self.graph.get_state({"configurable": {"thread_id": thread_id}})
        return state.values if state else None