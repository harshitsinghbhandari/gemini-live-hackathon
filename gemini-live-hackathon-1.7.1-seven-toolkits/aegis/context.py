from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class AegisContext:
    session: Any = None
    user_id: str = "default_user"
    composio: Any = None
    is_executing_tool: bool = False
