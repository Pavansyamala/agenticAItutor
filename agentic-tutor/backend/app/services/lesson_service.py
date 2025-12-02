# backend/app/services/lesson_service.py
from backend.app.schemas.tutor_schemas import TutorPlanResponse
from typing import Dict, Any


class LessonService:
    @staticmethod
    def format_plan_for_frontend(plan_data: Dict[str, Any]) -> TutorPlanResponse:
        """Normalize raw tutor output for consistent frontend consumption"""
        return TutorPlanResponse(**plan_data)