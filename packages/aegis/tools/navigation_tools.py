import json
import logging
from typing import Any, Dict
from google import genai
from google.genai import types
import base64

from .base import BaseTool, registry
from .context import get_current_view
from .. import config
from .. import prompt
from ..screen.window import get_active_window_bounds, get_all_visible_windows
from ..screen.cursor import position

logger = logging.getLogger("aegis.tools.navigation")

class SmartPlanTool(BaseTool):
    @property
    def name(self) -> str:
        return "smart_plan"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Ask the AI Architect (Gemini Pro) to break down a complex request into a step-by-step strategy. Use this for multi-stage tasks like messaging, drafting, or navigating complex apps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "The high-level goal, e.g. 'Search for Harshit on WhatsApp and say hello'"}
                },
                "required": ["goal"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        goal = args.get("goal")
        if not goal:
            return {"success": False, "error": "Missing required argument: goal"}
        
        shot = get_current_view()
        query_prompt = prompt.SMART_PLAN_PROMPT_TEMPLATE.format(goal=goal)
        
        try:
            # Use Gemini Pro for complex reasoning
            client_pro = genai.Client(api_key=config.GOOGLE_API_KEY)
            response = await client_pro.aio.models.generate_content(
                model=config.GEMINI_PRO_MODEL,
                contents=[
                    types.Part.from_bytes(
                        data=base64.b64decode(shot["base64"]),
                        mime_type=shot["mime_type"]
                    ),
                    query_prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            plan = json.loads(response.text)
            return {
                "success": True,
                "action": self.name,
                "plan": plan,
                "message": "Planning complete. Live Agent (Operator) will now follow this script."
            }
        except Exception as e:
            logger.error(f"Strategist failed: {e}")
            return {"success": False, "error": f"Planning failed: {str(e)}"}

class VerifyUIStateTool(BaseTool):
    @property
    def name(self) -> str:
        return "verify_ui_state"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Perform a visual check to ensure the screen matches expectations (e.g., 'Is the search results list visible?'). Use this between plan steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expected": {"type": "string", "description": "What you expect to see on screen, e.g. 'WhatsApp contact list'"}
                },
                "required": ["expected"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        expected = args.get("expected")
        if not expected:
            return {"success": False, "error": "Missing required argument: expected"}
        
        shot = get_current_view()
        query_prompt = prompt.VERIFY_UI_STATE_PROMPT_TEMPLATE.format(expected=expected)
        
        try:
            client = genai.Client(api_key=config.GOOGLE_API_KEY)
            response = await client.aio.models.generate_content(
                model=config.GEMINI_MODEL, # Flash is fine for fast verification
                contents=[
                    types.Part.from_bytes(
                        data=base64.b64decode(shot["base64"]),
                        mime_type=shot["mime_type"]
                    ),
                    query_prompt
                ]
            )
            verified = "YES" in response.text.upper()
            return {
                "success": True,
                "action": self.name,
                "verified": verified,
                "reason": response.text
            }
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {"success": False, "error": f"Verification failed: {str(e)}"}

class PlanCompleteTool(BaseTool):
    @property
    def name(self) -> str:
        return "plan_complete"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Signal that the current execution plan is finished and the task is complete. This re-enables the microphone.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Context clearing is handled by voice.py, but we confirm success here.
        return {
            "success": True, 
            "action": self.name, 
            "message": "Plan marked as complete. Aegis is now listening for new commands."
        }

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

registry.register(SmartPlanTool())
registry.register(VerifyUIStateTool())
registry.register(PlanCompleteTool())
registry.register(GetEnvironmentContextTool())
