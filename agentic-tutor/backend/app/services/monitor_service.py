# backend/app/services/monitor_service.py
from backend.app.schemas.monitor_schemas import MonitorDecision
from typing import Dict, Any


class MonitorService:
    @staticmethod
    def should_escalate(decision: Dict[str, Any]) -> bool:
        return decision.get("escalate", False)

    @staticmethod
    def needs_remediation(decision: Dict[str, Any]) -> bool:
        return not decision.get("allow_advance", True)

    @staticmethod
    def parse_decision(raw: Dict[str, Any]) -> MonitorDecision:
        return MonitorDecision(**raw)