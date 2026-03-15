import json
import logging
from typing import Any, Dict
from google import genai
from google.genai import types
import base64

from aegis.tools.base import BaseTool, registry
from aegis.tools.context import get_current_view
from configs.agent import config
from configs.agent.config import prompt
from aegis.perception.window import get_active_window_bounds, get_all_visible_windows
from aegis.perception.cursor import position

logger = logging.getLogger("aegis.tools.navigation")


class GetEnvironmentContextTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_environment_context"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Get current desktop environment context: the frontmost app name, visible window titles, and cursor position. Call this when you are disoriented or unsure which app or window is in focus before taking an action.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        active = get_active_window_bounds()
        all_windows = get_all_visible_windows()
        cursor_pos = position()
        return {
            "success": True,
            "action": self.name,
            "app_name": active.get("app_name", "Unknown") if active else "Unknown",
            "window_title": active.get("title", "") if active else "",
            "window_bounds": active if active else {},
            "all_visible_windows": [
                {"app": w["app_name"], "title": w["title"]}
                for w in all_windows
            ],
            "cursor_x": cursor_pos.get("x"),
            "cursor_y": cursor_pos.get("y"),
        }

registry.register(GetEnvironmentContextTool())
