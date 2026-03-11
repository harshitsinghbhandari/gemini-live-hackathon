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
import random
from google import genai
from google.genai import types

from . import config
from .screen.capture import capture_screen
from .screen.cursor import (
    move, click, double_click, right_click, scroll, drag, position, nudge, get_retina_scale
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
        "description": "Move the cursor to a specific bounding box center without clicking.",
        "parameters": {
            "type": "object",
            "properties": {
                "box_2d": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                }
            },
            "required": ["box_2d"]
        }
    },
    {
        "name": "cursor_click",
        "description": "Move cursor to bounding box center and left-click. Use screen_capture first to determine correct coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "box_2d": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                },
                "description": {"type": "string", "description": "What you are clicking on, e.g. 'Submit button', 'Chrome icon'"}
            },
            "required": ["box_2d", "description"]
        }
    },
    {
        "name": "cursor_double_click",
        "description": "Move cursor to bounding box center and double-click.",
        "parameters": {
            "type": "object",
            "properties": {
                "box_2d": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                },
                "description": {"type": "string", "description": "What you are double-clicking on"}
            },
            "required": ["box_2d", "description"]
        }
    },
    {
        "name": "cursor_right_click",
        "description": "Move cursor to bounding box center and right-click to open context menu.",
        "parameters": {
            "type": "object",
            "properties": {
                "box_2d": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                },
                "description": {"type": "string", "description": "What you are right-clicking on"}
            },
            "required": ["box_2d", "description"]
        }
    },
    {
        "name": "cursor_scroll",
        "description": "Scroll up or down at a specific bounding box center.",
        "parameters": {
            "type": "object",
            "properties": {
                "box_2d": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                },
                "clicks": {
                    "type": "integer",
                    "description": "Number of scroll clicks. Positive = up, negative = down. Use 3-5 for normal scroll."
                }
            },
            "required": ["box_2d", "clicks"]
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
        "description": "Type sensitive text like passwords or API keys. Clipboard is cleared immediately after.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The sensitive text to type"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "cursor_nudge",
        "description": "Move the cursor relative to its current position by exact pixels. Useful for fine-grained correction.",
        "parameters": {
            "type": "object",
            "properties": {
                "offset_x": {"type": "integer", "description": "Pixel adjustment on X axis (positive=right, negative=left)"},
                "offset_y": {"type": "integer", "description": "Pixel adjustment on Y axis (positive=down, negative=up)"}
            },
            "required": ["offset_x", "offset_y"]
        }
    },
    {
        "name": "screen_crop",
        "description": "Request a high-resolution crop of a specific Region of Interest (ROI). Use this to get a clearer view of a small area before clicking.",
        "parameters": {
            "type": "object",
            "properties": {
                "box_2d": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[ymin, xmin, ymax, xmax] (0-1000 scale) of the region to crop"
                }
            },
            "required": ["box_2d"]
        }
    },
    {
        "name": "cursor_target",
        "description": "Show a red target overlay at the specified bounding box and return a Verification Snapshot. Use this to verify accuracy BEFORE clicking. Follow up with cursor_confirm_click or cursor_nudge.",
        "parameters": {
            "type": "object",
            "properties": {
                "box_2d": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[ymin, xmin, ymax, xmax] (0-1000 scale) to target"
                }
            },
            "required": ["box_2d"]
        }
    },
    {
        "name": "cursor_confirm_click",
        "description": "Click exactly where the red target overlay was last placed.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


class WindowContext:
    def __init__(self):
        self.crop_origin_x = 0
        self.crop_origin_y = 0
        self.crop_width = None
        self.crop_height = None
        self.last_target_x = None
        self.last_target_y = None

window_state = WindowContext()

def reset_view():
    window_state.crop_origin_x = 0
    window_state.crop_origin_y = 0
    window_state.crop_width = None
    window_state.crop_height = None

def get_current_view():
    """Returns a full screenshot, or a zoomed-in crop if screen_crop is active."""
    if window_state.crop_width is not None and window_state.crop_height is not None:
        from .screen.capture import capture_region
        px = int(window_state.crop_origin_x)
        py = int(window_state.crop_origin_y)
        pw = int(window_state.crop_width)
        ph = int(window_state.crop_height)
        return capture_region(px, py, pw, ph)
    else:
        from .screen.capture import capture_screen
        return capture_screen()

def get_noisy_center(box):
    """Calculate center of [ymin, xmin, ymax, xmax] with random noise."""
    import pyautogui
    ymin, xmin, ymax, xmax = box
    # 1. Normalized center
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    # 2. Add noise (+- 5 normalized units)
    cx += random.uniform(-5, 5)
    cy += random.uniform(-5, 5)
    # 3. Clamp to 0-1000
    cx = max(0, min(1000, cx))
    cy = max(0, min(1000, cy))
    
    # 4. Handle Foveated Vision (Crop offset mapping)
    if window_state.crop_width is not None and window_state.crop_height is not None:
        logical_x = window_state.crop_origin_x + (cx / 1000) * window_state.crop_width
        logical_y = window_state.crop_origin_y + (cy / 1000) * window_state.crop_height
    else:
        screen_w, screen_h = pyautogui.size()
        logical_x = (cx / 1000) * screen_w
        logical_y = (cy / 1000) * screen_h
    
    target_x = int(logical_x)
    target_y = int(logical_y)
    
    return target_x, target_y


# ─────────────────────────────────────────────
# Tool dispatcher
# Maps tool name → actual function call
# ─────────────────────────────────────────────

async def _dispatch(tool_name: str, args: dict) -> dict:
    """Execute a screen tool by name with given args."""

    client = genai.Client(api_key=config.GOOGLE_API_KEY)

    try:
        if tool_name == "screen_capture":
            reset_view()
            shot = get_current_view()
            return {
                "success": True,
                "action": "screen_capture",
                "width": shot["width"],
                "height": shot["height"],
                "note": "Screenshot captured and available for Gemini analysis"
            }

        elif tool_name == "screen_read":
            question = args.get("question", "Describe everything you see on screen.")
            reset_view()
            shot = get_current_view()

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

        elif tool_name == "screen_crop":
            if "box_2d" not in args:
                return {"success": False, "error": "Missing required argument: box_2d"}
            
            box = args["box_2d"]
            ymin, xmin, ymax, xmax = box
            
            if window_state.crop_width is not None and window_state.crop_height is not None:
                base_x = window_state.crop_origin_x
                base_y = window_state.crop_origin_y
                base_w = window_state.crop_width
                base_h = window_state.crop_height
            else:
                import pyautogui
                base_x = 0
                base_y = 0
                base_w, base_h = pyautogui.size()
                
            x = base_x + (xmin / 1000) * base_w
            y = base_y + (ymin / 1000) * base_h
            w = ((xmax - xmin) / 1000) * base_w
            h = ((ymax - ymin) / 1000) * base_h
            
            # Store logical location for future global-to-local mapping
            window_state.crop_origin_x = x
            window_state.crop_origin_y = y
            window_state.crop_width = w
            window_state.crop_height = h
            
            return {
                "success": True,
                "action": "screen_crop",
                "message": "Crop captured successfully. Use this high-res context for precision actions."
            }

        elif tool_name == "cursor_target":
            if "box_2d" not in args:
                return {"success": False, "error": "Missing required argument: box_2d"}
            
            px, py = get_noisy_center(args["box_2d"])
            
            # AppKit overlay inherently accepts logical coordinates
            import subprocess, sys, os
            script_path = os.path.join(os.path.dirname(__file__), "screen", "overlay.py")
            subprocess.Popen([sys.executable, script_path, str(int(px)), str(int(py)), "30", "1500"])
            
            # Allow time for window to appear
            await asyncio.sleep(0.15)
            
            # Set a 200x200 crop around the target for the verification snapshot
            window_state.crop_origin_x = max(0, px - 100)
            window_state.crop_origin_y = max(0, py - 100)
            window_state.crop_width = 200
            window_state.crop_height = 200
            
            window_state.last_target_x = px
            window_state.last_target_y = py
            
            return {
                "success": True,
                "action": "cursor_target",
                "message": "Red target drawn. A verification thumbnail will be returned in the next turn. If perfectly centered, use cursor_confirm_click."
            }

        elif tool_name == "cursor_confirm_click":
            if window_state.last_target_x is None or window_state.last_target_y is None:
                return {"success": False, "error": "No target set. Use cursor_target first."}
            return click(int(window_state.last_target_x), int(window_state.last_target_y))

        elif tool_name == "cursor_move":
            if "box_2d" not in args:
                return {"success": False, "error": "Missing required argument: box_2d"}
            cx, cy = get_noisy_center(args["box_2d"])
            return move(int(cx), int(cy))

        elif tool_name == "cursor_click":
            if "box_2d" not in args:
                return {"success": False, "error": "Missing required argument: box_2d"}
            cx, cy = get_noisy_center(args["box_2d"])
            return click(int(cx), int(cy))

        elif tool_name == "cursor_double_click":
            if "box_2d" not in args:
                return {"success": False, "error": "Missing required argument: box_2d"}
            cx, cy = get_noisy_center(args["box_2d"])
            return double_click(int(cx), int(cy))

        elif tool_name == "cursor_right_click":
            if "box_2d" not in args:
                return {"success": False, "error": "Missing required argument: box_2d"}
            cx, cy = get_noisy_center(args["box_2d"])
            return right_click(int(cx), int(cy))

        elif tool_name == "cursor_scroll":
            if "box_2d" not in args or "clicks" not in args:
                return {"success": False, "error": "Missing required arguments: box_2d, clicks"}
            cx, cy = get_noisy_center(args["box_2d"])
            return scroll(int(cx), int(cy), args["clicks"])

        elif tool_name == "cursor_drag":
            if any(k not in args for k in ["x1", "y1", "x2", "y2"]):
                return {"success": False, "error": "Missing required arguments: x1, y1, x2, y2"}
            return drag(args["x1"], args["y1"], args["x2"], args["y2"])

        elif tool_name == "cursor_nudge":
            if "offset_x" not in args or "offset_y" not in args:
                return {"success": False, "error": "Missing required arguments: offset_x, offset_y"}
            return nudge(args["offset_x"], args["offset_y"])

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