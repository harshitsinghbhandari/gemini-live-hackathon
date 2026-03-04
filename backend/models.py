from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class ActionLog(BaseModel):
    timestamp: str
    action: str
    tier: str
    tool: Optional[str]
    toolkit: Optional[str] = None
    arguments: Dict[str, Any]
    auth_used: bool
    confirmed_verbally: bool
    blocked: bool
    success: bool
    error: Optional[str]
    duration_ms: int
    device: str

class AuthRequest(BaseModel):
    action: str
    tier: str
    reason: str
    speak: str
    tool: str
    arguments: Dict[str, Any]
    device: str

class AuthApproval(BaseModel):
    approved: bool

class AuthStatus(BaseModel):
    status: str # "pending" | "approved" | "denied"
    resolved_at: Optional[datetime] = None

class AuditEntry(ActionLog):
    id: str
