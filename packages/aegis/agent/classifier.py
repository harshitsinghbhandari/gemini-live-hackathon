from google.genai import types
import logging
import json
import re
from typing import Dict, Any, Optional
from google import genai
from configs.agent import config
from configs.agent.config import prompt

logger = logging.getLogger("aegis.classifier")

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
    Classifies the proposed action using Gemini.
    If tool_hint is provided, we skip tool selection and only determine the tier.
    """
    try:
        client = genai.Client(api_key=config.GOOGLE_API_KEY)

        if tool_hint:
            system_instruction = prompt.CLASSIFY_WITH_HINT_PROMPT_TEMPLATE.format(
                tool_hint=tool_hint,
                proposed_action=proposed_action,
                tier_rules_summary=prompt.TIER_RULES_SUMMARY_PRODUCTION
            )
            prompt_text = "Determine the security tier for this action."
        else:
            system_instruction = prompt.RISK_PROMPT_TESTING
            prompt_text = f"Proposed action: {proposed_action}"

        response = await client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[prompt_text],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=1024
            )
        )

        if not response or not response.text:
            logger.error("Empty response from Gemini during classification.")
            return {"tier": "RED", "reason": "Classification failed", "upgraded": True, "speak": "I encountered an error and must block this action for safety.", "tool": None, "arguments": {}}

        classification = parse_response(response.text)
        if not classification:
            # Fallback to safe state
            return {"tier": "RED", "reason": "Failed to parse classification", "upgraded": True, "speak": "I encountered an error and must block this action for safety.", "tool": None, "arguments": {}}

        return classification

    except Exception as e:
        logger.exception(f"Unexpected error during action classification: {e}")
        return {"tier": "RED", "reason": f"Classification error: {e}", "upgraded": True, "speak": "I encountered an error and must block this action for safety.", "tool": None, "arguments": {}}
