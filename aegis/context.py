from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum, auto

class SessionState(Enum):
    LISTENING = auto()
    THINKING = auto()
    EXECUTING = auto()
    DEAD = auto()

@dataclass
class AegisContext:
    session: Any = None
    user_id: str = "default_user"
    composio: Any = None
    state: SessionState = SessionState.LISTENING
    session_handle: Optional[str] = None

    @property
    def is_executing_tool(self) -> bool:
        return self.state == SessionState.EXECUTING

    @property
    def is_model_responding(self) -> bool:
        return self.state == SessionState.THINKING
