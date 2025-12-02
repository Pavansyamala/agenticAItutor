# backend/app/schemas/monitor_schemas.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class RemediationPlan(BaseModel):
    action: str  # remedial, practice, review, accelerate
    steps: List[str]
    recommended_tutor_mode: str


class MonitorDecision(BaseModel):
    allow_advance: bool
    remediation_plan: Optional[RemediationPlan] = None
    escalate: bool = False
    notes_for_teacher: str = ""