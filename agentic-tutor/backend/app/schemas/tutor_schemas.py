# backend/app/schemas/tutor_schemas.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID


class LessonStep(BaseModel):
    step: str
    duration_min: int
    content: str
    questions: Optional[List[Dict[str, Any]]] = None
    post_eval_specs: Optional[Dict[str, Any]] = None


class TutorPlanResponse(BaseModel):
    plan: List[LessonStep]
    expected_metrics: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class StartSessionRequest(BaseModel):
    student_id: str
    topic: str
    thread_id: Optional[str] = None