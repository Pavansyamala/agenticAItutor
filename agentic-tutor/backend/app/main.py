# backend/app/main.py
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.app.core.orchestrator import Orchestrator  # ← Now LangGraph-based
from backend.app.database.session import init_db

# Keep all your beautiful schemas
from backend.app.schemas.tutor_schemas import StartSessionRequest, TutorPlanResponse
from backend.app.schemas.evaluator_schemas import GradeRequest, StudentAnswer
from backend.app.schemas.monitor_schemas import MonitorDecision
from backend.app.services.evaluation_service import EvaluationService
from backend.app.services.monitor_service import MonitorService
from backend.app.database.models import Event
from backend.app.database.session import get_session
from sqlalchemy import or_

load_dotenv()

app = FastAPI(
    title="Adaptive Agentic Teaching Assistant for Linear Algebra",
    description="LangGraph-powered multi-agent system with RAG, SymPy, and mastery tracking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
orch = Orchestrator()  # ← Now REAL LangGraph with state + checkpoints


@app.get("/")
async def root():
    return {"message": "Agentic Tutor Running", "orchestrator": "LangGraph", "status": "ready"}


# ==================== 1. START SESSION ====================
@app.post("/api/session/start")
async def start_session(request: StartSessionRequest):
    result = await orch.start_session(request.student_id, request.topic)
    return {
        "thread_id": result["thread_id"],
        "status": "session_started",
        "message": f"Teaching {request.topic} to {request.student_id}"
    }


# ==================== 2. SUBMIT ANSWERS (Main Loop) ====================
@app.post("/api/eval/submit")
async def submit_answers(
    thread_id: str,
    answers: list[StudentAnswer]
):
    """
    This is the core learning loop:
    - Student submits answers
    - LangGraph resumes from checkpoint
    - Runs: grade → monitor → decide → loop or advance
    """
    result = await orch.submit_answers(
        thread_id=thread_id,
        answers=[a.dict() for a in answers]
    )

    # Use your existing services for clean output
    grading_summary = EvaluationService.build_grading_summary(result["grading"] or {})
    decision = MonitorService.parse_decision(result["decision"] or {})

    return {
        "thread_id": thread_id,
        "grading": grading_summary.dict(),
        "monitor_decision": decision.dict(),
        "next_action": result["next_action"],
        "session_continues": result["next_action"] != "advance"
    }


# ==================== 3. GET CURRENT STATE (For Frontend) ====================
@app.get("/api/session/{thread_id}")
async def get_session_state(thread_id: str):
    state = orch.get_state(thread_id)
    return {
        "thread_id": thread_id,
        "current_topic": state.get("topic"),
        "lesson_plan": state.get("lesson_plan"),
        "questions": state.get("questions"),
        "monitor_decision": state.get("monitor_decision"),
        "next_action": state.get("next_action")
    }


# ==================== DEBUG ENDPOINTS (Keep if needed) ====================
@app.get("/api/health")
async def health():
    return {"status": "healthy", "orchestrator": "LangGraph", "checkpoint_db": "checkpoints.db"}

@app.get("/api/events")
async def get_events(student_id: str = None, thread_id: str = None):
    with get_session() as session:
        query = session.query(Event)
        if student_id:
            query = query.filter(Event.student_id == student_id)
        if thread_id:
            query = query.filter(Event.payload.contains({"thread_id": thread_id}))
        events = query.order_by(Event.created_at.desc()).limit(50).all()
        
        return {
            "events": [
                {
                    "event_type": e.event_type,
                    "created_at": e.created_at.isoformat(),
                    "payload": e.payload,
                    "student_id": str(e.student_id) if e.student_id else None
                }
                for e in events
            ]
        }


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=5005, reload=True)