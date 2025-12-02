# backend/app/services/evaluation_service.py
from typing import List, Dict, Any
from backend.app.schemas.evaluator_schemas import GradingResult


class EvaluationService:
    @staticmethod
    def extract_overall_score(grading: Dict[str, Any]) -> float:
        return grading.get("overall_score", 0.0)

    @staticmethod
    def extract_misconceptions(grading: Dict[str, Any]) -> List[str]:
        return grading.get("misconceptions", [])

    @staticmethod
    def build_grading_summary(grading: Dict[str, Any]) -> GradingResult:
        return GradingResult(
            grading=grading.get("grading", {}),
            overall_score=grading.get("overall_score", 0.0),
            misconceptions=grading.get("misconceptions", [])
        )