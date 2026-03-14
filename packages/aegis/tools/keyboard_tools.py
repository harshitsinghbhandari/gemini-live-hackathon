import asyncio
from typing import Any, Dict
from aegis.tools.base import BaseTool, registry
from aegis.perception.screen.type import (
    type_text, press_key, hotkey, type_sensitive
)

class KeyboardTypeTool(BaseTool):
    @property
    def name(self) -> str:
        return "keyboard_type"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Type text into the currently focused input field. Click the field first if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to type"}
                },
                "required": ["text"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "text" not in args:
            return {"success": False, "error": "Missing required argument: text"}
        # ⚡ Bolt: Offload blocking pyautogui type_text call to thread pool to prevent event loop stall
        return await asyncio.to_thread(type_text, args["text"])


class KeyboardPressTool(BaseTool):
    @property
    def name(self) -> str:
        return "keyboard_press"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Press a single key by name, e.g. enter, escape, tab, backspace, up, down.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key name: enter, escape, tab, space, backspace, delete, up, down, left, right, f1-f12"
                    }
                },
                "required": ["key"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "key" not in args:
            return {"success": False, "error": "Missing required argument: key"}
        # ⚡ Bolt: Offload blocking pyautogui press_key call to thread pool to prevent event loop stall
        return await asyncio.to_thread(press_key, args["key"])

class KeyboardHotkeyTool(BaseTool):
    @property
    def name(self) -> str:
        return "keyboard_hotkey"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Press a keyboard shortcut combination, e.g. Cmd+C, Cmd+Space, Cmd+Tab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keys to press simultaneously, e.g. ['command', 'c'] or ['command', 'space']"
                    }
                },
                "required": ["keys"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        keys = args.get("keys")
        if not keys:
            return {"success": False, "error": "Missing required argument: keys (list of strings)"}
        # ⚡ Bolt: Offload blocking pyautogui hotkey call to thread pool to prevent event loop stall
        return await asyncio.to_thread(hotkey, *keys)

class KeyboardTypeSensitiveTool(BaseTool):
    @property
    def name(self) -> str:
        return "keyboard_type_sensitive"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Type sensitive text like passwords or API keys. Clipboard is cleared immediately after.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The sensitive text to type"}
                },
                "required": ["text"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "text" not in args:
            return {"success": False, "error": "Missing required argument: text"}
        # ⚡ Bolt: Offload blocking pyautogui type_sensitive call to thread pool to prevent event loop stall
        return await asyncio.to_thread(type_sensitive, args["text"])

registry.register(KeyboardTypeTool())
registry.register(KeyboardPressTool())
registry.register(KeyboardHotkeyTool())
registry.register(KeyboardTypeSensitiveTool())
