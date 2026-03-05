import logging
import json
import re
from typing import Dict, Any, Optional
from google import genai
from . import config

logger = logging.getLogger("aegis.classifier")

RISK_PROMPT = """
You are a security classifier for an AI agent controlling a Mac computer.

You will be given:
1. A proposed action the agent wants to take

Respond ONLY with valid JSON:
{
  "tier": "RED" | "YELLOW" | "GREEN",
  "reason": "one sentence explanation",
  "upgraded": true | false,
  "speak": "what to say to the user before acting",
  "tool": "COMPOSIO_TOOL_NAME",
  "arguments": {}
}

Tier rules:
- RED: irreversible financial transactions, deletes important/sensitive data,
  sends emails to ANY address, sends to NEW or EXTERNAL contacts,
  installs/uninstalls software, posts publicly on any platform
- YELLOW: creating drafts to ANY email address, replies to existing contacts,
  moves or renames files, form submissions, creates calendar events,
  sends messages on Slack/Teams to existing contacts
- GREEN: read-only actions ONLY — fetching, searching, viewing, checking,
  listing anything. No writing, no creating, no sending.

CRITICAL EXAMPLES:
- "fetch my emails" → GREEN (read-only)
- "check my calendar" → GREEN (read-only)
- "create a draft email" → YELLOW (creates something, involves external address)
- "reply to an email" → YELLOW (existing contact, reversible as draft first)
- "send an email" → RED (irreversible, external contact)
- "delete a file" → RED (irreversible)
- "create a calendar event" → YELLOW (reversible, additive)
- "pay an invoice" → RED (financial, irreversible)

Tool mapping with required arguments:
- GMAIL_FETCH_EMAILS: {"max_results": 5, "label_ids": ["INBOX"], "verbose": false}
- GMAIL_CREATE_EMAIL_DRAFT: {"to": "<extract from action>", "subject": "<extract>", "body": "<extract>"}
- GMAIL_REPLY_TO_THREAD: {"thread_id": "<extract>", "body": "<extract>"}
- GOOGLECALENDAR_GET_EVENTS: {"calendar_id": "primary", "max_results": 5}
- GOOGLECALENDAR_CREATE_EVENT: {"summary": "<extract>", "start_date_time": "<extract>", "end_date_time": "<extract>", "calendar_id": "primary"}

IMPORTANT:
- Always extract concrete values from the action description into arguments
- Never leave required fields empty
- When in doubt between two tiers, always choose the MORE restrictive one
- speak should NEVER ask for confirmation on GREEN actions — just state what you're doing
- speak should ask "shall I proceed?" on YELLOW actions
- speak should clearly state what requires biometric auth on RED actions
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

async def classify_action(proposed_action: str) -> Dict[str, Any]:
    """Classifies the proposed action using Gemini."""
    try:
        client = genai.Client(api_key=config.GOOGLE_API_KEY)

        response = await client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                {
                    "parts": [
                        {"text": f"Proposed action: {proposed_action}\n\n{RISK_PROMPT}"}
                    ]
                }
            ]
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
