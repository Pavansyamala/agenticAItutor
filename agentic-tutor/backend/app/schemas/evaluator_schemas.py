# backend/app/schemas/evaluator_schemas.py
from pydantic import BaseModel
from typing import List, Dict, Any


class Question(BaseModel):
    qid: str
    type: str
    prompt: str
    expected_solution: str
    rubric: Dict[str, Any]


class GenerateQuestionsRequest(BaseModel):
    topic: str
    q_types: List[str]
    counts: Dict[str, int]
    rag_context: str = ""


class StudentAnswer(BaseModel):
    qid: str
    answer: str


class GradeRequest(BaseModel):
    student_id: str
    topic: str
    eval_record: Dict[str, Any]
    student_answers: List[StudentAnswer]


class GradingResult(BaseModel):
    grading: Dict[str, Any]
    overall_score: float
    misconceptions: List[str] = []