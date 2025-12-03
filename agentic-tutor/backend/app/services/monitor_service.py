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
        print(raw)
        print("I am printed...")
        raw.setdefault("allow_advance", raw.get("next_action", "") == "remediation")
        raw.setdefault("confidence", 0.75)
        raw.setdefault("remediation_plan", None)
        raw.setdefault("notes_for_teacher", "")

        return MonitorDecision(**raw)