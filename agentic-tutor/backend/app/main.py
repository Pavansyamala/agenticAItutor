# backend/app/main.py
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential  # pip install tenacity

from backend.app.core.orchestrator import Orchestrator
from backend.app.database.session import init_db, get_session
from backend.app.database.models import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Singleton Orchestrator (global, persists memory across requests)
orchestrator = Orchestrator()

# ==================== FastAPI App ====================
app = FastAPI(
    title="Adaptive Agentic Teaching Assistant for Linear Algebra",
    description="LangGraph-powered multi-agent tutor with RAG, mastery tracking, and real-time monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None
)

# CORS — allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Prod: Restrict to localhost:8501
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
init_db()

# ==================== Request Models ====================
class StartSessionRequest(BaseModel):
    student_id: str
    topic: str

class StudentAnswer(BaseModel):
    qid: str
    answer: str

# ==================== Retry Decorator for API Calls ====================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
async def safe_orchestrator_call(func, *args, **kwargs):
    """Wrapper for exponential backoff on 429s/timeouts."""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if "429" in str(e) or "RateLimit" in str(e):
            logger.warning(f"Rate limit hit, backing off: {e}")
            raise  # Retry will catch
        logger.error(f"Orchestrator call failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Routes ====================

@app.get("/")
async def root():
    return {
        "message": "Adaptive Linear Algebra Tutor is LIVE",
        "orchestrator": "LangGraph + MemorySaver (Singleton Active)",
        "status": "ready",
        "docs": "/docs"
    }

# 1. Start a new tutoring session (only generates lesson)
@app.post("/api/session/start")
async def start_session(request: StartSessionRequest):
    async def _start():
        return await orchestrator.start_session(request.student_id, request.topic)
    try:
        result = await safe_orchestrator_call(_start)
        return {
            "thread_id": result["thread_id"],
            "lesson_plan": result.get("lesson_plan"),
            "status": "lesson_ready",
            "message": f"Started teaching {request.topic}"
        }
    except Exception as e:
        logger.error(f"Start session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. Submit answers → triggers full evaluation cycle (generate questions if none, grade, monitor, decide)
@app.post("/api/eval/submit")
async def submit_answers(
    thread_id: str = Query(..., description="Active session thread"),
    answers: List[StudentAnswer] = []
):
    """
    Core learning loop:
    - If answers = [] → just generate questions
    - If answers provided → grade + monitor + decide next action
    """
    async def _submit():
        # Convert Pydantic models → dicts
        answer_dicts = [a.dict() for a in answers]
        return await orchestrator.submit_answers(thread_id, answer_dicts)

    try:
        result = await safe_orchestrator_call(_submit)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        # Extract clean, frontend-friendly response
        grading_result = result.get("grading", {}) or {}
        monitor_decision = result.get("decision", {}) or {}
        allow_advance = monitor_decision.get("allow_advance", False)

        return {
            "thread_id": thread_id,
            "status": "success",
            "questions": result.get("questions", []),
            "grading": {
                "overall_score": grading_result.get("overall_score"),
                "misconceptions": grading_result.get("misconceptions", []),
                "per_question": grading_result.get("grading", {})
            },
            "monitor_decision": monitor_decision,
            "allow_advance": allow_advance,
            "next_action": "advance" if allow_advance else "continue",
            "message": "Evaluation complete" if answers else "Questions generated"
        }
    except Exception as e:
        logger.error(f"Submit answers failed for {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

# 3. Get current session state (for live UI updates)
@app.get("/api/session/{thread_id}")
async def get_session_state(thread_id: str):
    try:
        state = orchestrator.get_state(thread_id)
        if not state:
            raise HTTPException(status_code=404, detail="Session not found or expired")

        return {
            "thread_id": thread_id,
            "topic": state.get("topic"),
            "lesson_plan": state.get("lesson_plan"),
            "questions": state.get("questions"),
            "grading_result": state.get("grading_result"),
            "monitor_decision": state.get("monitor_decision"),
            "allow_advance": state.get("allow_advance", False),
            "remediation_plan": state.get("remediation_plan"),
            "messages": state.get("messages", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get state failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session state")

# 4. Get student mastery profile (for radar chart + PDF export)
@app.get("/api/student/{student_id}/profile")
async def get_student_profile(student_id: str):
    try:
        with get_session() as session:
            from backend.app.database.models import StudentProfile
            profile = session.query(StudentProfile).filter(StudentProfile.student_id == student_id).first()
            if not profile:
                return {
                    "student_id": student_id,
                    "mastery_map": {},
                    "misconceptions": [],
                    "overall_score": 0.0,
                    "sessions_completed": 0
                }
            return {
                "student_id": profile.student_id,
                "mastery_map": profile.mastery_map or {},
                "misconceptions": profile.misconceptions or [],
                "overall_score": profile.overall_score or 0.0,
                "risk_score": profile.risk_score or 0.0,
                "learning_style": profile.learning_preferences or {}
            }
    except Exception as e:
        logger.error(f"Profile fetch failed: {e}")
        return {"mastery_map": {}, "misconceptions": []}

# 5. Real-time event log (for Session Timeline tab) – Fixed filter for thread_id
@app.get("/api/events")
async def get_events(
    student_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    limit: int = 100
):
    try:
        with get_session() as session:
            query = session.query(Event)
            if student_id:
                query = query.filter(Event.student_id == student_id)
            if thread_id:
                # Better filter: Exact match on payload.thread_id
                query = query.filter(Event.payload['thread_id'].astext == thread_id)  # SQLAlchemy JSON op
            events = query.order_by(Event.created_at.desc()).limit(limit).all()

            return {
                "events": [
                    {
                        "event_type": e.event_type.replace("_", " ").title(),
                        "created_at": e.created_at.isoformat(),
                        "payload": e.payload,
                        "student_id": e.student_id
                    }
                    for e in events
                ]
            }
    except Exception as e:
        logger.error(f"Events fetch failed: {e}")
        return {"events": []}

# Health check – Expose active sessions count (for demo)
@app.get("/api/health")
async def health():
    # Quick hack: Count threads in memory (expand for prod)
    active = len(orchestrator.memory.get_all_checkpoints() or [])  # LangGraph API
    return {
        "status": "healthy",
        "orchestrator": "LangGraph with MemorySaver",
        "active_sessions": active,
        "rag_ready": True
    }

# ==================== Run Server ====================
if __name__ == "__main__":
    print("\n🚀 Starting Adaptive Agentic Tutor (LangGraph + FastAPI)")
    print("   Frontend: http://localhost:8501")
    print("   API Docs: http://127.0.0.1:5010/docs\n")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=5010, reload=True, log_level="info")

# backend/app/main.py

# import uvicorn
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from dotenv import load_dotenv

# from backend.app.core.orchestrator_no_graph import Orchestrator
# from backend.app.schemas.tutor_schemas import StartSessionRequest
# from backend.app.schemas.evaluator_schemas import StudentAnswer

# app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"]
# )

# orch = Orchestrator()

# @app.post("/api/session/start")
# async def start_session(req: StartSessionRequest):
#     return await orch.start_session(req.student_id, req.topic)

# @app.post("/api/session/start_quiz")
# async def start_quiz(thread_id: str):
#     return await orch.start_quiz(thread_id)

# @app.post("/api/eval/submit")
# async def submit_answers(thread_id: str, answers: list[StudentAnswer]):
#     ans = [a.dict() for a in answers]
#     return await orch.submit_answers(thread_id, ans)

# @app.get("/api/session/{thread_id}")
# async def state(thread_id: str):
#     return orch.get_state(thread_id)

# if __name__ == "__main__":
#     uvicorn.run("backend.app.main:app", host="127.0.0.1", port=5006, reload=True)
