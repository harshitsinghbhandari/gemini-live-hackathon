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

from configs.agent import config
from configs.agent.config import prompt
from aegis.perception.screen.capture import capture_screen
from aegis.tools import registry
from aegis.tools.declarations import get_screen_tool_declarations
from aegis.tools.context import window_state, reset_view, get_current_view, get_noisy_center

SCREEN_TOOL_DECLARATIONS = get_screen_tool_declarations()

logger = logging.getLogger("aegis.screen_executor")


# ─────────────────────────────────────────────
# Tool dispatcher
# Maps tool name → actual function call
# ─────────────────────────────────────────────

async def _dispatch(tool_name: str, args: dict) -> dict:
    """Execute a screen tool by name with given args using the ToolRegistry."""
    return await registry.dispatch(tool_name, args)


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
    return tool_name.startswith(("screen_", "cursor_", "keyboard_", "browser_")) or tool_name in ["smart_plan", "verify_ui_state", "plan_complete", "get_environment_context"]


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
                    text=prompt.SCREEN_AGENT_SYSTEM_PROMPT_TEMPLATE.format(user_command=user_command)
                )
            ]
        )
    ]

    import os
    steps = []

    MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "50"))
    for step in range(min(max_steps, MAX_STEPS)):
        response = await client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=messages,
            config=types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=SCREEN_TOOL_DECLARATIONS)],
                max_output_tokens=1024
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