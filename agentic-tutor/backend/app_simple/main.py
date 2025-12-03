# backend/app_simple/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
from backend.app.core.orchestrator import Orchestrator
orchestrator = Orchestrator()


app = FastAPI(title="Agentic Tutor - Simple Backend")

# --- In-memory stores (replace with DB for production) ---
SESSIONS: Dict[str, Dict[str, Any]] = {}
PROFILES: Dict[str, Dict[str, Any]] = {}

# --- Pydantic models ---
class StartSessionRequest(BaseModel):
    student_id: str
    topic: str

class Question(BaseModel):
    qid: str
    type: str
    prompt: str
    expected_solution: str
    possible: int = 10

class StudentAnswer(BaseModel):
    qid: str
    answer: str

class SubmitPayload(BaseModel):
    answers: List[StudentAnswer]

# ---------------- Utility / Simple Tutors & Grader ----------------
def make_lesson(topic: str) -> List[Dict[str,str]]:
    # Simple deterministic lesson for demo
    if "eigen" in topic.lower():
        steps = [
            {"step": 1, "title": "Eigenvalue definition",
             "content": "For a square matrix A, λ is an eigenvalue if det(A - λI) = 0. Eigenvectors satisfy A v = λ v."},
            {"step": 2, "title": "Interpretation",
             "content": "Eigenvalues indicate scaling along invariant directions (eigenvectors). They relate to stability and frequencies."},
            {"step": 3, "title": "Worked example",
             "content": "Example: A = [[4,1],[1,3]] → eigenvalues 5 and 2; eigenvectors ..."}
        ]
    else:
        steps = [
            {"step": 1, "title": "Intro", "content": f"Lesson on {topic}."}
        ]
    return steps

def generate_questions_for(topic: str) -> List[Dict[str, Any]]:
    # Deterministic small question set (you can replace with LLM or RAG)
    if "eigen" in topic.lower():
        qs = [
            {"qid":"Q1", "type":"conceptual",
             "prompt":"State the fundamental equation for eigenvalues of a square matrix.",
             "expected_solution":"det(A-λ*I)=0","possible":10},
            {"qid":"Q2", "type":"procedural",
             "prompt":"For A = [[2,1],[1,2]], compute eigenvalues.",
             "expected_solution":"3,1","possible":10},
            {"qid":"Q3", "type":"application",
             "prompt":"If eigenvalues of a system matrix are -1 and -2, is the system stable?",
             "expected_solution":"yes","possible":10}
        ]
    else:
        qs = [
            {"qid":"Q1", "type":"conceptual", "prompt":f"What is {topic}?", "expected_solution":"", "possible":10}
        ]
    return qs

def simple_grade(questions: List[Dict[str,Any]], answers: List[Dict[str,str]]) -> Dict[str, Any]:
    # naive grader: substring matching / simple checks
    grading = {}
    total_obtained = 0
    total_possible = 0
    misconceptions = []
    for q in questions:
        qid = q["qid"]
        expected = (q.get("expected_solution") or "").lower().strip()
        possible = q.get("possible", 10)
        total_possible += possible
        provided = ""
        for a in answers:
            if a.get("qid") == qid:
                provided = a.get("answer","").lower().strip()
                break
        obtained = 0
        feedback = ""
        if expected == "":
            # no expected solution: give partial credit if any answer provided
            if provided:
                obtained = int(possible * 0.8)
                feedback = "Answer received."
            else:
                obtained = 0
                feedback = "No answer provided."
        else:
            # simple checks
            if expected in provided:
                obtained = possible
                feedback = "Correct (simple match)."
            elif provided == "":
                obtained = 0
                feedback = "No answer provided."
            else:
                obtained = 0
                feedback = f"Expected: {q.get('expected_solution')}. Please review."
                misconceptions.append(f"{qid}: incomplete or incorrect for concept '{q.get('type')}'")
        grading[qid] = {"obtained": obtained, "possible": possible, "feedback": feedback}
        total_obtained += obtained

    overall_score = 0.0
    if total_possible > 0:
        overall_score = round(total_obtained / total_possible, 3)
    return {"overall_score": overall_score, "grading": grading, "misconceptions": misconceptions}

def monitor_decision_from_eval(eval_summary: Dict[str,Any], policy: Dict[str,Any]) -> Dict[str,Any]:
    overall = float(eval_summary.get("overall_score", 0.0))
    mastery = float(policy.get("mastery_threshold", 0.8))
    escalate_threshold = float(policy.get("escalate_threshold", 0.4))
    decision = {"allow_advance": False, "remediation_plan": None, "escalate": False, "notes_for_teacher": ""}

    if overall >= mastery:
        decision["allow_advance"] = True
        decision["remediation_plan"] = None
    else:
        decision["allow_advance"] = False
        decision["remediation_plan"] = {
            "action": "remedial" if overall < 0.5 else "practice",
            "steps": [
                "Review the core definitions and examples.",
                "Complete 3 targeted practice exercises with hints.",
                "Re-attempt the short quiz."
            ],
            "recommended_tutor_mode": "revision"
        }

    if overall < escalate_threshold:
        decision["escalate"] = True
        decision["notes_for_teacher"] = "Student scored below escalate threshold - consider human review."

    return decision

# ---------------- Endpoints ----------------
@app.post("/api/session/start")
def start_session(req: StartSessionRequest):
    thread_id = f"{req.student_id}_{uuid.uuid4().hex[:8]}"
    lesson = make_lesson(req.topic)
    session_state = {
        "student_id": req.student_id,
        "topic": req.topic,
        "thread_id": thread_id,
        "lesson_plan": lesson,
        "questions": [],
        "student_answers": [],
        "grading_result": None,
        "monitor_decision": None,
        "created_at": datetime.utcnow().isoformat()
    }
    SESSIONS[thread_id] = session_state
    # Ensure profile exists
    if req.student_id not in PROFILES:
        PROFILES[req.student_id] = {"student_id": req.student_id, "mastery_map": {}, "misconceptions": [], "history": []}
    return {"thread_id": thread_id, "status": "session_started", "lesson_plan": lesson}

@app.post("/api/session/{thread_id}/generate_questions")
def generate_questions(thread_id: str):
    session = SESSIONS.get(thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    qs = generate_questions_for(session["topic"])
    session["questions"] = qs
    session["student_answers"] = []
    session["grading_result"] = None
    session["monitor_decision"] = None
    return {"questions": qs}

@app.post("/api/session/{thread_id}/submit_answers")
def submit_answers(thread_id: str, payload: SubmitPayload):
    session = SESSIONS.get(thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    questions = session.get("questions", [])
    answers = [a.dict() for a in payload.answers]
    session["student_answers"] = answers

    # Grade
    grading = simple_grade(questions, answers)
    session["grading_result"] = grading

    # Build eval_summary for monitor
    eval_summary = {
        "overall_score": grading["overall_score"],
        "grading": grading["grading"],
        "misconceptions": grading["misconceptions"],
        "confidence_gap": 0.0,
        "time_taken": 0.0
    }

    # dynamic policy (simple)
    policy = {"mastery_threshold": 0.8, "escalate_threshold": 0.4, "consec_required": 2}
    decision = monitor_decision_from_eval(eval_summary, policy)
    session["monitor_decision"] = decision

    # update profile history & mastery_map simple
    profile = PROFILES.get(session["student_id"], {"mastery_map": {}, "misconceptions": [], "history": []})
    profile["history"].append({"ts": datetime.utcnow().isoformat(), "score": grading["overall_score"], "topic": session["topic"]})
    # update naive mastery
    prev = profile["mastery_map"].get(session["topic"], 0.0)
    profile["mastery_map"][session["topic"]] = round(max(prev, grading["overall_score"]), 3)
    profile["misconceptions"] = list({*profile.get("misconceptions", []), *grading.get("misconceptions", [])})
    PROFILES[session["student_id"]] = profile

    return {"grading": grading, "monitor_decision": decision}

@app.get("/api/session/{thread_id}")
def get_session_state(thread_id: str):
    s = SESSIONS.get(thread_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s

@app.get("/api/profile/{student_id}")
def get_profile(student_id: str):
    p = PROFILES.get(student_id)
    if not p:
        # return empty profile
        return {"student_id": student_id, "mastery_map": {}, "misconceptions": [], "history": []}
    return p
