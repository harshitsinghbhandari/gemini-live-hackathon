import asyncio
import json
import re
import os
from dotenv import load_dotenv
from google import genai
from .screen_capture import capture_screen
from .auth import request_touch_id
from .composio_executor import execute_action

load_dotenv()

RISK_PROMPT = """
You are a security classifier for an AI agent controlling a Mac computer.

You will be given:
1. A screenshot of the current screen
2. A proposed action the agent wants to take

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
  sends to NEW or EXTERNAL contacts, installs/uninstalls software
- YELLOW: replies to EXISTING contacts, moves files, form submissions,
  sends to known internal contacts, small file deletions
- GREEN: read-only, additive only, checking/viewing anything

Available tools:
- GMAIL_FETCH_EMAILS: fetch emails, arguments: {"max_results": 5}
- GMAIL_CREATE_EMAIL_DRAFT: create draft, arguments: {"to": "", "subject": "", "body": ""}
- GMAIL_FORWARD_MESSAGE: forward email, arguments: {"message_id": "", "to": ""}

Map the proposed action to the best tool and arguments.
"""

async def classify_action(screenshot_b64: str, proposed_action: str) -> dict:
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=[{
            "parts": [
                {"text": f"Proposed action: {proposed_action}\n\n{RISK_PROMPT}"},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": screenshot_b64
                }}
            ]
        }]
    )
    clean = re.sub(r"```json|```", "", response.text).strip()
    return json.loads(clean)

async def gate_action(proposed_action: str) -> dict:
    print(f"\n🤖 Proposed action: {proposed_action}")

    screenshot = await capture_screen()
    classification = await classify_action(screenshot, proposed_action)

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
        print("🟡 YELLOW — needs confirmation")
        result["needs_confirmation"] = True
        return result

    elif tier == "GREEN":
        print("🟢 GREEN — executing silently")

    # Execute via Composio
    if tool:
        output = await execute_action(tool, arguments)
        result["output"] = output

    result["executed"] = True
    return result