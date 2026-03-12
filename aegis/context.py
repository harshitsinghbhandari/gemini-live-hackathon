from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum, auto

class SessionState(Enum):
    LISTENING = auto()
    THINKING = auto()
    EXECUTING = auto()
    BUSY = auto()

@dataclass
class AegisContext:
    session: Any = None
    user_id: str = "default_user"
    state: SessionState = SessionState.LISTENING
    resumption_handle: Optional[Any] = None
    ocr_cache: dict = None  # populated by aegis.screen.ocr background loop
    ocr_idle_delay: float = 0.5 # Default idle delay for OCR loop
    
    # Smart Planning
    execution_plan: list = None  # List of dicts [{"action": "...", "verify": "...", ...}]
    plan_index: int = 0

    # Verification Gate (Phase 3)
    plan_halted: bool = False      # Set True when a verification step fails
    plan_halt_reason: str = ""     # Human-readable explanation for the halt
    verification_passed: bool = False  # Set True when verify_ui_state returns SUCCESS

    @property
    def is_executing_tool(self) -> bool:
        return self.state == SessionState.EXECUTING

    @is_executing_tool.setter
    def is_executing_tool(self, value: bool):
        if value:
            self.state = SessionState.EXECUTING
        elif self.state == SessionState.EXECUTING:
            self.state = SessionState.LISTENING

    @property
    def is_model_responding(self) -> bool:
        return self.state in (SessionState.THINKING, SessionState.EXECUTING, SessionState.BUSY)

    @is_model_responding.setter
    def is_model_responding(self, value: bool):
        if value:
            if self.state == SessionState.LISTENING:
                self.state = SessionState.THINKING
        else:
            self.state = SessionState.LISTENING
