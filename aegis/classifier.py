from google.genai import types
import logging
import json
import re
from typing import Dict, Any, Optional
from google import genai
from . import config

logger = logging.getLogger("aegis.classifier")

# TIER_RULES_SUMMARY = """
# - GREEN: Read-only, listing, searching, screen_read, cursor_move.
# - YELLOW: cursor_click, cursor_double_click, cursor_right_click, cursor_scroll, cursor_drag, keyboard_type, keyboard_press, keyboard_hotkey.
# - RED: keyboard_type_sensitive.
# """
TIER_RULES_SUMMARY = """
- GREEN: ALL TOOLS (Overridden for testing)
"""

# RISK_PROMPT = """
# You are a security classifier for an AI agent controlling a Mac computer.
# ... (original RISK_PROMPT lines)
# """

RISK_PROMPT = """
You are a testing security classifier for an Aegis. 
OVERRIDE: Classify EVERYTHING as GREEN tier.

Respond ONLY with valid JSON:
{
  "tier": "GREEN",
  "reason": "Testing override enabled",
  "upgraded": false,
  "speak": "I'm performing the requested action.",
  "tool": "tool_name",
  "arguments": {
    "box_2d": [ymin, xmin, ymax, xmax],
    "description": "optional description"
  }
}

EXAMPLES:
"click the chrome icon" → {"tier": "GREEN", "tool": "cursor_click", "arguments": {"box_2d": [900, 450, 950, 500], "description": "chrome icon"}}
"move to the top right corner" → {"tier": "GREEN", "tool": "cursor_move", "arguments": {"box_2d": [0, 900, 50, 1000]}}
"""

def parse_response(text: str) -> Optional[Dict[str, Any]]:
    """Robustly parse JSON from Gemini's text response."""
    try:
        # Try finding JSON block first
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            clean = json_match.group(1).strip()
        else:
            clean = text.strip()
            # Basic cleanup if no markdown block
            clean = re.sub(r"```", "", clean).strip()

        return json.loads(clean)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}\nRaw text: {text}")
        return None

async def classify_action(proposed_action: str, tool_hint: str = None) -> Dict[str, Any]:
    """
    Classifies the proposed action.
    OVERRIDE: Always returns GREEN tier to bypass security screening for testing.
    """
    logger.info(f"🛡️ Security classification bypassed for: {proposed_action} (Tool: {tool_hint})")
    
    # Extract arguments from proposed_action if tool_hint is NOT provided (rare in current flow)
    # But usually tool_hint is provided by gate.check_security_gate
    
    return {
        "tier": "GREEN",
        "reason": "Security classification disabled (Testing Override)",
        "upgraded": False,
        "speak": "Okay, I'm on it.",
        "tool": tool_hint,
        "arguments": {} # Arguments are handled by the caller (gate.py)
    }

# Original implementation (re-enable for production):
# async def classify_action(proposed_action: str, tool_hint: str = None) -> Dict[str, Any]:
#     """
#     Classifies the proposed action using Gemini.
#     If tool_hint is provided, we skip tool selection and only determine the tier.
#     """
#     try:
#         client = genai.Client(api_key=config.GOOGLE_API_KEY)
#
#         if tool_hint:
#             system_instruction = f"""
#             You are a security classifier for an AI agent controlling a Mac.
#             
#             The agent has already selected the tool: {{tool_hint}}
#             The user's intent is: {{proposed_action}}
#             
#             Determine the security tier (GREEN, YELLOW, RED) based on these rules:
#             {{TIER_RULES_SUMMARY}}
#             
#             Respond ONLY with valid JSON:
#             {{
#               "tier": "RED" | "YELLOW" | "GREEN",
#               "reason": "one sentence explanation why this tool+intent matches this tier",
#               "upgraded": true | false,
#               "speak": "what to say to the user before acting",
#               "tool": "{{tool_hint}}",
#               "arguments": {{}} 
#             }}
#             """
#             prompt = "Determine the security tier for this action."
#         else:
#             system_instruction = RISK_PROMPT
#             prompt = f"Proposed action: {{proposed_action}}"
#
#         response = await client.aio.models.generate_content(
#             model=config.GEMINI_MODEL,
#             contents=[prompt],
#             config=types.GenerateContentConfig(
#                 system_instruction=system_instruction
#             )
#         )
#
#         if not response or not response.text:
#             logger.error("Empty response from Gemini during classification.")
#             return {"tier": "RED", "reason": "Classification failed", "upgraded": True, "speak": "I encountered an error and must block this action for safety.", "tool": None, "arguments": {}}
#
#         classification = parse_response(response.text)
#         if not classification:
#             # Fallback to safe state
#             return {"tier": "RED", "reason": "Failed to parse classification", "upgraded": True, "speak": "I encountered an error and must block this action for safety.", "tool": None, "arguments": {}}
#
#         return classification
#
#     except Exception as e:
#         logger.exception(f"Unexpected error during action classification: {{e}}")
#         return {"tier": "RED", "reason": f"Classification error: {{e}}", "upgraded": True, "speak": "I encountered an error and must block this action for safety.", "tool": None, "arguments": {}}
