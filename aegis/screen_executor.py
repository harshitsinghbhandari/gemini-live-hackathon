"""
aegis/screen_executor.py

Executes screen control actions using Gemini native function calling.
Bypasses Composio Tool Router entirely — direct execution, zero routing overhead.

Tool naming convention:
  screen_*   → capture / read
  cursor_*   → mouse actions
  keyboard_* → keyboard actions

Tier classification (enforced by gate.py before this is called):
  GREEN  → screen_capture, screen_read, cursor_move
  YELLOW → cursor_click, cursor_double_click, cursor_right_click,
            cursor_scroll, cursor_drag, keyboard_type,
            keyboard_hotkey, keyboard_press
  RED    → keyboard_type_sensitive
"""

import asyncio
import base64
import json
import logging
from google import genai
from google.genai import types

from . import config
from .screen.capture import capture_screen
from .screen.cursor import (
    move, click, double_click, right_click, scroll, drag, position
)
from .screen.type import (
    type_text, press_key, hotkey, type_sensitive
)

logger = logging.getLogger("aegis.screen_executor")


# ─────────────────────────────────────────────
# Gemini Function Declarations
# These are sent to Gemini so it knows exactly
# what tools are available and what args to pass.
# ─────────────────────────────────────────────

SCREEN_TOOL_DECLARATIONS = [
    {
        "name": "screen_capture",
        "description": "Take a screenshot of the current screen. Use this first before any click or type action to understand what is on screen and get accurate coordinates.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "screen_read",
        "description": "Take a screenshot and describe what is currently visible on screen — apps, windows, text, buttons, and UI elements.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Optional specific question about the screen, e.g. 'Where is the search bar?' or 'Is Chrome open?'"
                }
            },
            "required": []
        }
    },
    {
        "name": "cursor_move",
        "description": "Move the cursor to specific coordinates without clicking.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate (0-1470)"},
                "y": {"type": "integer", "description": "Y coordinate (0-956)"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "cursor_click",
        "description": "Move cursor to coordinates and left-click. Use screen_capture first to determine correct coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate (0-1470)"},
                "y": {"type": "integer", "description": "Y coordinate (0-956)"},
                "description": {"type": "string", "description": "What you are clicking on, e.g. 'Submit button', 'Chrome icon'"}
            },
            "required": ["x", "y", "description"]
        }
    },
    {
        "name": "cursor_double_click",
        "description": "Move cursor to coordinates and double-click.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate (0-1470)"},
                "y": {"type": "integer", "description": "Y coordinate (0-956)"},
                "description": {"type": "string", "description": "What you are double-clicking on"}
            },
            "required": ["x", "y", "description"]
        }
    },
    {
        "name": "cursor_right_click",
        "description": "Move cursor to coordinates and right-click to open context menu.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate (0-1470)"},
                "y": {"type": "integer", "description": "Y coordinate (0-956)"},
                "description": {"type": "string", "description": "What you are right-clicking on"}
            },
            "required": ["x", "y", "description"]
        }
    },
    {
        "name": "cursor_scroll",
        "description": "Scroll up or down at specific coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate to scroll at"},
                "y": {"type": "integer", "description": "Y coordinate to scroll at"},
                "clicks": {
                    "type": "integer",
                    "description": "Number of scroll clicks. Positive = up, negative = down. Use 3-5 for normal scroll."
                }
            },
            "required": ["x", "y", "clicks"]
        }
    },
    {
        "name": "cursor_drag",
        "description": "Click and drag from one coordinate to another.",
        "parameters": {
            "type": "object",
            "properties": {
                "x1": {"type": "integer", "description": "Start X coordinate"},
                "y1": {"type": "integer", "description": "Start Y coordinate"},
                "x2": {"type": "integer", "description": "End X coordinate"},
                "y2": {"type": "integer", "description": "End Y coordinate"}
            },
            "required": ["x1", "y1", "x2", "y2"]
        }
    },
    {
        "name": "keyboard_type",
        "description": "Type text into the currently focused input field. Click the field first if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to type"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "keyboard_press",
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
    },
    {
        "name": "keyboard_hotkey",
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
    },
    {
        "name": "keyboard_type_sensitive",
        "description": "Type sensitive text like passwords or API keys. Requires biometric authentication (RED tier). Clipboard is cleared immediately after.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The sensitive text to type"}
            },
            "required": ["text"]
        }
    }
]


# ─────────────────────────────────────────────
# Tool dispatcher
# Maps tool name → actual function call
# ─────────────────────────────────────────────

async def _dispatch(tool_name: str, args: dict) -> dict:
    """Execute a screen tool by name with given args."""

    client = genai.Client(api_key=config.GOOGLE_API_KEY)

    try:
        if tool_name == "screen_capture":
            shot = capture_screen()
            return {
                "success": True,
                "action": "screen_capture",
                "width": shot["width"],
                "height": shot["height"],
                "note": "Screenshot captured and available for Gemini analysis"
            }

        elif tool_name == "screen_read":
            question = args.get("question", "Describe everything you see on screen.")
            shot = capture_screen()

            # Ask Gemini to describe the screen
            try:
                response = await client.aio.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=[
                        types.Part.from_bytes(
                            data=base64.b64decode(shot["base64"]),
                            mime_type=shot["mime_type"]
                        ),
                        question
                    ]
                )
                return {
                    "success": True,
                    "action": "screen_read",
                    "description": response.text
                }
            except Exception as e:
                logger.error(f"Error in screen_read: {e}")
                return {"success": False, "error": f"Gemini analysis failed: {str(e)}"}

        elif tool_name == "cursor_move":
            if "x" not in args or "y" not in args:
                return {"success": False, "error": "Missing required arguments: x, y"}
            return move(args["x"], args["y"])

        elif tool_name == "cursor_click":
            if "x" not in args or "y" not in args:
                return {"success": False, "error": "Missing required arguments: x, y"}
            return click(args["x"], args["y"])

        elif tool_name == "cursor_double_click":
            if "x" not in args or "y" not in args:
                return {"success": False, "error": "Missing required arguments: x, y"}
            return double_click(args["x"], args["y"])

        elif tool_name == "cursor_right_click":
            if "x" not in args or "y" not in args:
                return {"success": False, "error": "Missing required arguments: x, y"}
            return right_click(args["x"], args["y"])

        elif tool_name == "cursor_scroll":
            if "x" not in args or "y" not in args or "clicks" not in args:
                return {"success": False, "error": "Missing required arguments: x, y, clicks"}
            return scroll(args["x"], args["y"], args["clicks"])

        elif tool_name == "cursor_drag":
            if any(k not in args for k in ["x1", "y1", "x2", "y2"]):
                return {"success": False, "error": "Missing required arguments: x1, y1, x2, y2"}
            return drag(args["x1"], args["y1"], args["x2"], args["y2"])

        elif tool_name == "keyboard_type":
            if "text" not in args:
                return {"success": False, "error": "Missing required argument: text"}
            return type_text(args["text"])

        elif tool_name == "keyboard_press":
            if "key" not in args:
                return {"success": False, "error": "Missing required argument: key"}
            return press_key(args["key"])

        elif tool_name == "keyboard_hotkey":
            keys = args.get("keys")
            if not keys:
                return {"success": False, "error": "Missing required argument: keys (list of strings)"}
            return hotkey(*keys)

        elif tool_name == "keyboard_type_sensitive":
            if "text" not in args:
                return {"success": False, "error": "Missing required argument: text"}
            return type_sensitive(args["text"])

        else:
            return {"success": False, "error": f"Unknown screen tool: {tool_name}"}
            
    except Exception as e:
        logger.exception(f"Unexpected error in _dispatch for {tool_name}: {e}")
        return {"success": False, "error": f"Internal execution error: {str(e)}"}


# ─────────────────────────────────────────────
# Main entry point
# Called by gate.py after auth is cleared
# ─────────────────────────────────────────────

async def execute_screen_action(tool_name: str, args: dict) -> dict:
    """
    Execute a screen action.
    
    Args:
        tool_name: One of the SCREEN_TOOL_DECLARATIONS names
        args: Arguments dict matching the tool's parameter schema
    
    Returns:
        dict with at minimum: {success: bool, action: str}
    """
    result = await _dispatch(tool_name, args)
    return result


def is_screen_tool(tool_name: str) -> bool:
    """
    Returns True if the tool name belongs to the screen executor.
    Used by gate.py to route to the correct executor.
    """
    return tool_name.startswith(("screen_", "cursor_", "keyboard_"))


# ─────────────────────────────────────────────
# Agentic loop
# Gemini sees screen, decides actions, executes
# in a loop until task is complete.
# ─────────────────────────────────────────────

async def run_screen_agent(user_command: str, max_steps: int = 10) -> dict:
    """
    Run a multi-step screen automation task.
    
    Gemini sees the screen, picks a tool, we execute it,
    feed result back, Gemini picks next tool, repeat
    until Gemini says task is done or max_steps reached.
    
    Args:
        user_command: Natural language instruction e.g. "Open Chrome and go to youtube.com"
        max_steps: Safety limit on number of actions
    
    Returns:
        dict: {success, steps_taken, final_state}
    """
    client = genai.Client(api_key=config.GOOGLE_API_KEY)

    # Start with a screenshot so Gemini knows what it's working with
    shot = capture_screen()

    messages = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(
                    data=base64.b64decode(shot["base64"]),
                    mime_type=shot["mime_type"]
                ),
                types.Part.from_text(
                    text=f"""You are Aegis, an AI agent controlling a Mac.
                    
Your task: {user_command}

Screen dimensions: 1470x956
You can see the current state of the screen above.

Use the available tools to complete the task step by step.
- Always use screen_capture before clicking to verify current state
- After each action, capture the screen again to verify it worked
- When the task is complete, respond with text only (no tool call) saying "Task complete: [what was done]"
"""
                )
            ]
        )
    ]

    steps = []

    for step in range(max_steps):
        response = await client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=messages,
            config=types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=SCREEN_TOOL_DECLARATIONS)]
            )
        )
        
        candidate = response.candidates[0]
        model_parts = candidate.content.parts

        # Check if Gemini is done (text response, no tool call)
        has_tool_call = any(part.function_call for part in model_parts if part.function_call)

        if not has_tool_call:
            final_text = " ".join(part.text for part in model_parts if part.text)
            return {
                "success": True,
                "steps_taken": len(steps),
                "steps": steps,
                "final_state": final_text
            }

        # Execute all tool calls in this response
        tool_responses = []
        for part in model_parts:
            if not part.function_call:
                continue

            tool_name = part.function_call.name
            args = dict(part.function_call.args)

            result = await _dispatch(tool_name, args)
            steps.append({"tool": tool_name, "args": args, "result": result})

            tool_responses.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response=result
                )
            )

        # Add Gemini's response (model turn) to messages
        messages.append(candidate.content)

        # Take fresh screenshot and add with tool results (user turn)
        fresh_shot = capture_screen()
        user_parts = tool_responses + [
            types.Part.from_bytes(
                data=base64.b64decode(fresh_shot["base64"]),
                mime_type=fresh_shot["mime_type"]
            ),
            types.Part.from_text(text="Updated screen state after your actions. Continue or confirm task complete.")
        ]
        messages.append(types.Content(role="user", parts=user_parts))

    return {
        "success": False,
        "steps_taken": len(steps),
        "steps": steps,
        "final_state": "Max steps reached without completing task"
    }


if __name__ == "__main__":
    # Quick smoke test — just read the screen, no actions
    async def main():
        print("Testing screen_executor — reading current screen state...")
        result = await execute_screen_action("screen_read", {"question": "What applications or windows are currently visible?"})
        print(f"\nScreen description:\n{result.get('description', result)}")

    asyncio.run(main())