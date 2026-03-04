import os
from dotenv import load_dotenv
import re
import json
load_dotenv()
from google import genai

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

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
  "arguments": {
    // extract ALL relevant parameters from the action description
    // for emails: to, subject, body
    // for calendar: summary, start_date_time, end_date_time
    // for fetching: max_results, label_ids
  }
}

Tier rules:
- RED: irreversible financial transactions, deletes important/sensitive data,
  sends to NEW or EXTERNAL contacts, installs/uninstalls software
- YELLOW: replies to EXISTING contacts, moves files, form submissions
- GREEN: read-only, additive only, checking/viewing anything

Tool mapping with required arguments:
- GMAIL_FETCH_EMAILS: {"max_results": 5, "label_ids": ["INBOX"], "verbose": false}
- GMAIL_CREATE_EMAIL_DRAFT: {"to": "<extract from action>", "subject": "<extract>", "body": "<extract>"}
- GMAIL_REPLY_TO_THREAD: {"thread_id": "<extract>", "body": "<extract>"}
- GOOGLECALENDAR_GET_EVENTS: {"calendar_id": "primary", "max_results": 5}
- GOOGLECALENDAR_CREATE_EVENT: {"summary": "<extract>", "start_date_time": "<extract>", "end_date_time": "<extract>", "calendar_id": "primary"}

IMPORTANT: Always extract concrete values from the action description into arguments.
Never leave required fields empty.
"""
def parse_response(text: str) -> dict:
    clean = re.sub(r"```json|```", "", text).strip()
    return json.loads(clean)
async def classify_action(proposed_action: str) -> dict:
    client = genai.Client()
    
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {
                "parts": [
                    {"text": f"Proposed action: {proposed_action}\n\n{RISK_PROMPT}"}
                ]
            }
        ]
    )
    
    return parse_response(response.text)