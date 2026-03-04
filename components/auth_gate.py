import asyncio
import json
import re
import os
from dotenv import load_dotenv
from google import genai
from .screen_capture import capture_screen
from .auth import request_touch_id
from .composio_executor import search_and_execute

load_dotenv()
# Add this at the top
_session = None  # will be injected from voice_agent.py

def set_session(session):
    """Inject the live session so auth gate can speak + listen"""
    global _session
    _session = session

async def request_yellow_confirmation(speak: str) -> bool:
    """
    Guardian speaks the confirmation request and listens for yes/no.
    Returns True if user confirms, False if denied.
    """
    if not _session:
        print("⚠️ No live session — defaulting to blocked")
        return False
    
    # Send confirmation request as text to Gemini
    # Gemini will speak it and listen for response
    await _session.send_client_content(
        turns=[{
            "role": "user",
            "parts": [{
                "text": f"""
                YELLOW tier action detected. 
                Say exactly this to the user: "{speak}. Should I proceed?"
                Then listen for their yes or no response.
                If they say yes or confirm → respond with exactly: CONFIRMED
                If they say no or cancel → respond with exactly: CANCELLED
                """
            }]
        }],
        turn_complete=True
    )
    
    # Listen for Gemini's classification of the user's response
    async for response in _session.receive():
        if response.server_content and response.server_content.model_turn:
            for part in response.server_content.model_turn.parts:
                if hasattr(part, 'text') and part.text:
                    text = part.text.strip().upper()
                    print(f"🟡 Confirmation response: {text}")
                    if "CONFIRMED" in text:
                        return True
                    if "CANCELLED" in text:
                        return False
        
        if response.server_content and response.server_content.turn_complete:
            break
    
    return False  # default to safe

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

async def classify_action(proposed_action: str) -> dict:
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=[{
            "parts": [
                {"text": f"Proposed action: {proposed_action}\n\n{RISK_PROMPT}"}
            ]
        }]
    )
    clean = re.sub(r"```json|```", "", response.text).strip()
    return json.loads(clean)

async def gate_action(proposed_action: str) -> dict:
    print(f"\n🤖 Proposed action: {proposed_action}")

    classification = await classify_action(proposed_action)

    tier = classification["tier"]
    speak = classification["speak"]
    tool = classification.get("tool")
    arguments = classification.get("arguments", {})

    print(f"🎯 Tier: {tier}")
    print(f"💬 Reason: {classification['reason']}")
    print(f"🗣️  Agent says: {speak}")
    print(f"🔧 Tool: {tool} | Args: {arguments}")

    result = {
        "action": proposed_action,
        "tier": tier,
        "reason": classification["reason"],
        "upgraded": classification["upgraded"],
        "tool": tool,
        "executed": False,
        "auth_used": False,
        "blocked": False
    }

    if tier == "RED":
        print("\n🔴 RED — requesting Touch ID...")
        authed = await request_touch_id(f"Guardian: {speak}")
        if not authed:
            print("🚫 Blocked!")
            result["blocked"] = True
            return result
        result["auth_used"] = True
        print("✅ Authenticated!")

    elif tier == "YELLOW":
        print("🟡 YELLOW — requesting verbal confirmation...")
        confirmed = await request_yellow_confirmation(speak)
        
        if not confirmed:
            print("🚫 User declined")
            result["blocked"] = True
            return result
        
        print("✅ User confirmed verbally!")
        result["confirmed_verbally"] = True

    elif tier == "GREEN":
        print("🟢 GREEN — executing silently")

    # Execute via Composio
    if tool:
        output = await search_and_execute(proposed_action, arguments)
        result["output"] = output

    result["executed"] = True
    return result