from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from backend.app.core.orchestrator import orchestrator

router = APIRouter()

class EvaluationRecord(BaseModel):
    questions: List[Dict[str, Any]]

class StudentAnswer(BaseModel):
    qid: str
    answer: str

class GradeRequest(BaseModel):
    eval_record: EvaluationRecord
    student_answers: List[StudentAnswer]


@router.post("/api/eval/grade")
async def grade(request: GradeRequest):
    result = await orchestrator.dispatch(
        "evaluator",
        "grade_answers",
        context={
            "goal_params": {
                "eval_record": request.eval_record.dict(),
                "student_answers": [a.dict() for a in request.student_answers]
            }
        }
    )
    return result
