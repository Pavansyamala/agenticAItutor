# backend/app/core/message_schema.py
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

class AgentMessage(BaseModel):
    message_id: UUID = uuid4()
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    goal: str
    goal_params: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    tools_allowed: List[str] = []
    hard_constraints: Dict[str, Any] = {}
    soft_constraints: Dict[str, Any] = {}

class AgentResponse(BaseModel):
    message_id: UUID
    status: str  # e.g., "ok", "needs_more_info", "error"
    plan: Optional[List[Dict[str, Any]]] = []
    result: Optional[Dict[str, Any]] = {}
    tool_calls: Optional[List[Dict[str, Any]]] = []
    metadata: Optional[Dict[str, Any]] = {}
