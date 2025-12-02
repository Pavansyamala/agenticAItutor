# backend/app/schemas/student_schemas.py
from pydantic import BaseModel
from typing import Dict, Any, List
from uuid import UUID


class StudentProfileResponse(BaseModel):
    student_id: UUID
    mastery_map: Dict[str, float]
    overall_score: float
    risk_score: float
    history: List[Dict[str, Any]]
    last_updated: str


class StudentCreate(BaseModel):
    name: str
    email: str