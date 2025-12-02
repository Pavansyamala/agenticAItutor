# # backend/app/core/orchestrator.py
# import uuid
# from typing import Dict, Any, List, Optional
# from backend.app.core.agent_registry import AgentRegistry
# from backend.app.core.message_schema import AgentMessage, AgentResponse
# from backend.app.core.llm_client import LLMClient


# class Orchestrator:
#     """
#     Central orchestrator for agentic workflows.

#     - Routes messages to registered agents
#     - Enforces constraints
#     - Uses LLMClient (Groq-powered) for any LLM needs
#     """

#     def __init__(self, registry: AgentRegistry):
#         self.registry = registry
#         self.llm = LLMClient(model="gpt-oss-20b")  # Groq fast model

#     async def dispatch(
#         self,
#         to_agent: str,
#         goal: str,
#         goal_params: Optional[Dict[str, Any]] = None,
#         context: Optional[Dict[str, Any]] = None,
#         tools_allowed: Optional[List[str]] = None,
#         constraints: Optional[Dict[str, Any]] = None,
#     ) -> AgentResponse:
#         """
#         Dispatch a goal to a registered agent.

#         Always merges goal_params into context["goal_params"] so all agents receive
#         properly structured inputs.
#         """

#         goal_params = goal_params or {}
#         context = context or {}
#         tools_allowed = tools_allowed or []
#         constraints = constraints or {"hard": {}, "soft": {}}

#         # Ensure context has a "goal_params" block
#         # so every agent run receives neatly packed arguments
#         ctx_goal_params = context.get("goal_params", {})
#         ctx_goal_params.update(goal_params)
#         context["goal_params"] = ctx_goal_params

#         # Unique ID for tracking
#         message_id = str(uuid.uuid4())

#         msg = AgentMessage(
#             message_id=message_id,
#             from_agent="orchestrator",
#             to_agent=to_agent,
#             goal=goal,
#             goal_params=ctx_goal_params,
#             context=context,
#             tools_allowed=tools_allowed,
#             hard_constraints=constraints.get("hard", {}),
#             soft_constraints=constraints.get("soft", {}),
#         )

#         # Fetch agent instance
#         agent = self.registry.get(to_agent)
#         if not agent:
#             return AgentResponse(
#                 message_id=message_id,
#                 status="error",
#                 result={"error": f"Agent '{to_agent}' not found in registry."}
#             )

#         # Execute agent
#         try:
#             result = await agent.run(goal=goal, context=msg.dict())
#             return AgentResponse(
#                 message_id=message_id,
#                 status="ok",
#                 result=result
#             )
#         except Exception as e:
#             return AgentResponse(
#                 message_id=message_id,
#                 status="error",
#                 result={"error": str(e)}
#             )



# # backend/app/core/orchestrator.py
# from typing import TypedDict, Annotated, List, Dict, Any
# from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.sqlite import SqliteSaver
# from backend.app.agents.tutor_agent import TutorAgent
# from backend.app.agents.evaluator_agent import EvaluatorAgent
# from backend.app.agents.monitor_agent import MonitorAgent
# from backend.app.core.agent_registry import AgentRegistry
# from backend.app.database.session import get_session
# import uuid

# # ------------------------------------------------------------------
# # State Definition (shared across all agents)
# # ------------------------------------------------------------------
# class AgentState(TypedDict):
#     student_id: str
#     topic: str
#     lesson_plan: Dict[str, Any]
#     questions: List[Dict[str, Any]]
#     student_answers: List[Dict[str, Any]]
#     grading_result: Dict[str, Any]
#     monitor_decision: Dict[str, Any]
#     messages: Annotated[List[Dict[str, str]], "append"]  # for logging
#     next: str  # routing control


# # ------------------------------------------------------------------
# # LangGraph Workflow
# # ------------------------------------------------------------------
# class Orchestrator:
#     def __init__(self):
#         self.registry = AgentRegistry()
#         self.tutor = TutorAgent()
#         self.evaluator = EvaluatorAgent()
#         self.monitor = MonitorAgent()

#         # Persist state across sessions (required for mastery tracking)
#         memory = SqliteSaver.from_conn_string("./checkpoints.db")
#         self.graph = self._build_graph(memory)

#     def _build_graph(self, memory):
#         workflow = StateGraph(AgentState)

#         # Nodes
#         workflow.add_node("tutor", self._call_tutor)
#         workflow.add_node("evaluator_generate", self._call_evaluator_generate)
#         workflow.add_node("evaluator_grade", self._call_evaluator_grade)
#         workflow.add_node("monitor", self._call_monitor)

#         # Edges
#         workflow.set_entry_point("tutor")
#         workflow.add_edge("tutor", "evaluator_generate")
#         workflow.add_edge("evaluator_generate", "evaluator_grade")
#         workflow.add_edge("evaluator_grade", "monitor")

#         # Conditional routing based on monitor decision
#         workflow.add_conditional_edges(
#             "monitor",
#             self._route_next,
#             {
#                 "remediate": "tutor",
#                 "practice": "evaluator_generate",
#                 "advance": END
#             }
#         )

#         return workflow.compile(checkpointer=memory)

#     # ------------------------------------------------------------------
#     # Node Functions
#     # ------------------------------------------------------------------
#     async def _call_tutor(self, state: AgentState) -> Dict[str, Any]:
#         result = await self.tutor.run(
#             goal="teach_topic",
#             context={
#                 "goal_params": {
#                     "topic": state["topic"],
#                     "student_id": state["student_id"],
#                     "target_mastery": 0.8
#                 }
#             }
#         )
#         return {
#             "lesson_plan": result.get("plan", []),
#             "messages": [{"role": "tutor", "content": "Lesson delivered"}],
#             "next": "evaluator_generate"
#         }

#     async def _call_evaluator_generate(self, state: AgentState) -> Dict[str, Any]:
#         result = await self.evaluator.run(
#             goal="generate_questions",
#             context={
#                 "goal_params": {
#                     "topic": state["topic"],
#                     "q_types": ["conceptual", "procedural", "application"],
#                     "counts": {"conceptual": 2, "procedural": 2, "application": 1},
#                     "rag_context": ""  # will be enhanced later with real RAG
#                 }
#             }
#         )
#         questions = result.get("questions", [])
#         return {
#             "questions": questions,
#             "messages": [{"role": "evaluator", "content": f"Generated {len(questions)} questions"}]
#         }

#     async def _call_evaluator_grade(self, state: AgentState) -> Dict[str, Any]:
#         if not state.get("student_answers"):
#             return {"grading_result": {}, "next": "monitor"}

#         result = await self.evaluator.run(
#             goal="grade_answers",
#             context={
#                 "goal_params": {
#                     "eval_record": {"questions": state["questions"]},
#                     "student_answers": state["student_answers"]
#                 }
#             }
#         )
#         return {"grading_result": result, "next": "monitor"}

#     async def _call_monitor(self, state: AgentState) -> Dict[str, Any]:
#         result = await self.monitor.run(
#             goal="decide",
#             context={
#                 "goal_params": {
#                     "student_id": state["student_id"],
#                     "grading": state.get("grading_result", {}),
#                     "topic": state["topic"]
#                 }
#             }
#         )
#         decision = result.get("remediation_plan", {}).get("action", "advance")
#         route_map = {
#             "remedial": "remediate",
#             "practice": "practice",
#             "review": "remediate",
#             "revision": "remediate",
#             "accelerate": "advance"
#         }
#         next_step = route_map.get(decision, "advance")

#         return {
#             "monitor_decision": result,
#             "messages": [{"role": "monitor", "content": f"Decision: {next_step}"}],
#             "next": next_step
#         }

#     def _route_next(self, state: AgentState) -> str:
#         return state["next"]

#     # ------------------------------------------------------------------
#     # Public API
#     # ------------------------------------------------------------------
#     async def start_session(self, student_id: str, topic: str, thread_id: str = None):
#         config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
#         initial_state = {
#             "student_id": student_id,
#             "topic": topic,
#             "student_answers": [],
#             "messages": []
#         }
#         async for output in self.graph.astream(initial_state, config):
#             pass  # stream updates if needed
#         return self.graph.get_state(config).values


# backend/app/core/orchestrator.py
from typing import TypedDict, Annotated, Literal, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
# from langgraph.prebuilt import tools
from backend.app.agents.tutor_agent import TutorAgent
from backend.app.agents.evaluator_agent import EvaluatorAgent
from backend.app.agents.monitor_agent import MonitorAgent
from backend.app.database.session import get_session
import uuid
from uuid import uuid4
from datetime import datetime
import logging
from backend.app.database.models import Event
from backend.app.database.session import get_session
from langgraph.checkpoint.memory import MemorySaver  # In-memory for dev (switch to SQLite later)
import datetime

from backend.app.core.rag.rag_service import RAGService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_event(student_id, event_type: str, payload: dict, thread_id: str = None ):
    with get_session() as session:
        event = Event(
            event_id = uuid.uuid4().hex,
            student_id=student_id,
            event_type=event_type,
            payload={**payload, "thread_id": thread_id},
            created_at=datetime.datetime.utcnow()
        )
        session.add(event)
        session.commit()

# =================================================================
# 1. Shared State — passed between all agents (LangGraph requirement)
# =================================================================
class AgentState(TypedDict):
    student_id: str
    topic: str
    thread_id: str

    # Tutor outputs
    lesson_plan: Optional[List[Dict[str, Any]]]
    tutor_messages: Annotated[List[Dict], "append"]

    # Evaluator outputs
    questions: Optional[List[Dict[str, Any]]]
    student_answers: Optional[List[Dict[str, Any]]]
    grading_result: Optional[Dict[str, Any]]

    # Monitor outputs
    monitor_decision: Optional[Dict[str, Any]]
    allow_advance: bool
    remediation_plan: Optional[Dict[str, Any]]
    next_action: Literal["teach", "evaluate", "remediate", "advance"]

    # RAG context (shared across agents)
    rag_context: str

    # History
    messages: Annotated[List[Dict[str, str]], "append"]


# =================================================================
# 2. LangGraph Orchestrator — FULLY STATEFUL + CONDITIONAL EDGES
# =================================================================
class Orchestrator:
    def __init__(self):
        self.tutor = TutorAgent()
        self.evaluator = EvaluatorAgent()
        self.monitor = MonitorAgent()

        # Inside __init__
        RAGService.initialize()  # Load curriculum at startup

        # Persistent checkpointing (required for long-term mastery)
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Nodes
        workflow.add_node("tutor", self.tutor_node)
        workflow.add_node("generate_questions", self.generate_questions_node)
        workflow.add_node("grade_answers", self.grade_answers_node)
        workflow.add_node("monitor", self.monitor_node)

        # Entry → Tutor
        workflow.set_entry_point("tutor")


        # Fixed flow
        workflow.add_edge("tutor", "generate_questions")
        workflow.add_edge("generate_questions", "grade_answers")
        workflow.add_edge("grade_answers", "monitor")

        # Conditional routing based on Monitor decision
        workflow.add_conditional_edges(
            "monitor",
            self.decide_next,
            {
                "teach": "tutor",
                "remediate": "tutor",
                "evaluate": "generate_questions",
                "advance": END
            }
        )

        return workflow.compile(checkpointer=self.memory)
        

    # =================================================================
    # Node Implementations
    # =================================================================
    async def tutor_node(self, state: AgentState) -> Dict[str, Any]:
        # 1. Get clean, focused RAG context
        rag_context = RAGService.get_context(
            query=f"explain {state['topic']} with examples and common misconceptions",
            use_tavily=True
        )

        # 2. Pass it PROPERLY — as embedded_context (exactly as your Evaluator does)
        result = await self.tutor.run(
            goal="teach_topic",
            context={
                "goal_params": {
                    "topic": state["topic"],           # ← Keep topic clean
                    "student_id": state["student_id"],
                    "target_mastery": 0.8,
                    "embedded_context": rag_context     # ← THIS is how you inject RAG
                }
            }
        )

        log_event(state["student_id"], "lesson_delivered", {
        "topic": state["topic"],
        "steps": len(result.get("plan", []))}, state["thread_id"]) 

        return {
            "lesson_plan": result.get("plan"),
            "tutor_messages": [{"role": "tutor", "content": "RAG-grounded lesson delivered"}],
            "messages": [{"role": "system", "content": f"Taught {state['topic']} with RAG context"}],
            "rag_context": rag_context  # optional: store for debugging
        }

    async def generate_questions_node(self, state: AgentState) -> Dict[str, Any]:
        rag_context = RAGService.get_context(state["topic"], use_tavily=True)
        
        result = await self.evaluator.run(
            goal="generate_questions",
            context={"goal_params": {
                "topic": state["topic"],
                "q_types": ["conceptual", "procedural", "application", "open-ended"],
                "counts": {"conceptual": 2, "procedural": 2, "application": 1, "open-ended": 1},
                "embedded_context": rag_context  # ← NOW INJECTED
            }}
        )

        print(result.get("questions", []))
        raw_questions = result.get("questions", [])

        questions = []
        for q in raw_questions:
            if (
                isinstance(q, dict)
                and "qid" in q
                and "type" in q
                and "prompt" in q
                and "expected_solution" in q
                and "rubric" in q
            ):
                questions.append(q)
            else:
                logger.warning(f"[Evaluator Warning] Dropped malformed question item: {q}")
        
        log_event(
            state["student_id"],
            "questions_generated",
            {
                "count": len(questions),
                "types": list({q["type"] for q in questions}) if questions else []
            },
            state["thread_id"]
        )

        
        return {
            "questions": questions,
            "rag_context": rag_context,
            "messages": [{"role": "rag", "content": "RAG context injected"}]
        }

    async def grade_answers_node(self, state: AgentState) -> Dict[str, Any]:
        if not state.get("student_answers"):
            return {"grading_result": None}

        result = await self.evaluator.run(
            goal="grade_answers",
            context={"goal_params": {
                "eval_record": {"questions": state["questions"]},
                "student_answers": state["student_answers"]
            }}
        )

        log_event(state["student_id"], "answers_graded", {
        "overall_score": result.get("overall_score", 0),
        "questions_count": len(result.get("grading", {})),
        "sympy_used": sum(1 for q in result.get("grading", {}).values() if q.get("sympy_used"))}, state["thread_id"])
        return {
            "grading_result": result,
            "messages": [{"role": "evaluator", "content": "Answers graded"}]
        }

    async def monitor_node(self, state: AgentState) -> Dict[str, Any]:
        result = await self.monitor.run(
            goal="decide",
            context={"goal_params": {
                "student_id": state["student_id"],
                "grading": state.get("grading_result", {}),
                "topic": state["topic"]
            }}
        )

        decision = result.get("remediation_plan", {})
        action = decision.get("action", "advance")
        allow_advance = result.get("allow_advance", True)

        log_event(state["student_id"], "monitor_decision", {
        "action": action,
        "allow_advance": result.get("allow_advance", True),
        "misconceptions": result.get("misconceptions", [])}, state["thread_id"])

        next_map = {
            "remedial": "remediate",
            "practice": "evaluate",
            "review": "teach",
            "revision": "teach",
            "accelerate": "advance"
        }
        next_step = next_map.get(action, "advance" if allow_advance else "remediate")

        retry_count = state.get("messages", []).count({"role": "monitor", "content": "Decision: remediate"}) if isinstance(state.get("messages"), list) else 0
        # Alternatively track a numeric counter in state like state.get("remediate_retries", 0)
        if retry_count >= 4:
            # force escalate or advance to break loop
            return {
                "allow_advance": False,
                "remediation_plan": {
                    "action": "remedial",
                    "steps": ["Please schedule human intervention."],
                    "recommended_tutor_mode": "revision"
                },
                "escalate": True,
                "notes_for_teacher": "Multiple remediation cycles detected — escalate to human."
            }

        return {
            "monitor_decision": result,
            "allow_advance": allow_advance,
            "remediation_plan": decision,
            "next_action": next_step,
            "messages": [{"role": "monitor", "content": f"Decision: {next_step}"}]
        }

    def decide_next(self, state: AgentState) -> str:
        return state["next_action"]

    # =================================================================
    # Public Methods — Used by main.py
    # =================================================================
    async def start_session(self, student_id: str, topic: str, thread_id: str = None):
        thread_id = f"{student_id}_{uuid.uuid4().hex}"   # 100% safe, no spaces, no &
        config = {"configurable": {"thread_id": thread_id},"recursion_limit": 5}
        log_event(student_id, "session_started", {"topic": topic}, thread_id)

        initial_state = {
            "student_id": student_id,
            "topic": topic,
            "thread_id": thread_id,
            "student_answers": [],
            "rag_context": "",
            "messages": [],
            "tutor_messages": []
        }

        async for output in self.graph.astream(initial_state, config):
            pass  # Can stream to frontend later

        return {"thread_id": thread_id, "status": "session_started"}

    async def submit_answers(self, thread_id: str, answers: List[Dict]):
        config = {"configurable": {"thread_id": thread_id},"recursion_limit": 6}
        current = self.graph.get_state(config).values
        updated = {**current, "student_answers": answers}

        async for output in self.graph.astream(updated, config):
            pass

        final = self.graph.get_state(config).values
        return {
            "grading": final.get("grading_result"),
            "decision": final.get("monitor_decision"),
            "next_action": final["next_action"]
        }

    def get_state(self, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.get_state(config).values