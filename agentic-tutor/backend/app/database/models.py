# backend/app/database/models.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import uuid

from sqlmodel import SQLModel, Field
from sqlalchemy import String
from sqlalchemy import JSON          # works for SQLite, MySQL, PostgreSQL (JSONB if you import JSONB)
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String
import uuid
from datetime import datetime
# ----------------------------------------------------------------------
# Helper: JSON column that defaults to {} / [] and allows NULL
# ----------------------------------------------------------------------
def json_field(default: Any) -> Any:
    """Return a JSON column with a mutable default."""
    return Field(default=default, sa_type=JSON)


# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------
class Student(SQLModel, table=True):
    student_id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    name: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # renamed to avoid shadowing SQLModel.metadata
    extra_data: Dict[str, Any] = json_field(default={})


class StudentProfile(SQLModel, table=True):
    student_id: str = Field(primary_key=True, foreign_key="student.student_id")
    mastery_map: Dict[str, float] = json_field(default={})
    overall_score: float = Field(default=0.0)
    learning_preferences: Dict[str, Any] = json_field(default={})
    risk_score: float = Field(default=0.0)
    history: List[Dict[str, Any]] = json_field(default=[])
    
    # ADD THIS LINE - THIS WAS MISSING!
    misconceptions: List[str] = Field(default_factory=list, sa_type=JSON)

    last_updated: datetime = Field(default_factory=datetime.utcnow)

class Evaluation(SQLModel, table=True):
    eval_id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: Optional[str] = Field(foreign_key="student.student_id")
    topic: str
    questions: List[Dict[str, Any]] = json_field(default=[])
    student_answers: List[Dict[str, Any]] = json_field(default=[])
    grading: Dict[str, Any] = json_field(default={})
    overall_score: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Event(SQLModel, table=True):
    event_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex,
        sa_column=Column(String, primary_key=True)  # <-- THIS FIXES IT
    )
    student_id: Optional[str] = Field(default=None, foreign_key="student.student_id" , index = True)
    event_type: str
    payload: Dict[str, Any] = json_field(default={})
    created_at: datetime = Field(default_factory=datetime.utcnow)