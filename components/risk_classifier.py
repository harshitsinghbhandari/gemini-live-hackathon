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
1. A screenshot of the current screen
2. A proposed action the agent wants to take

Your job: classify the risk tier of this action.

Respond ONLY with valid JSON:
{
  "tier": "RED" | "YELLOW" | "GREEN",
  "reason": "one sentence explanation",
  "upgraded": true | false,
  "speak": "what to say to the user before acting"
}

Tier rules:
- RED: irreversible, financial, deletes important data, sends to external contacts
- YELLOW: reversible but sensitive, needs human confirmation  
- GREEN: read-only, additive, low risk

IMPORTANT: If context makes an action riskier than it appears 
(e.g. file named 'tax-return', email going externally), UPGRADE the tier.
Set upgraded=true if you changed the default tier.
"""
def parse_response(text: str) -> dict:
    clean = re.sub(r"```json|```", "", text).strip()
    return json.loads(clean)
async def classify_action(screenshot_b64: str, proposed_action: str) -> dict:
    client = genai.Client()
    
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {
                "parts": [
                    {"text": f"Proposed action: {proposed_action}\n\n{RISK_PROMPT}"},
                    {"inline_data": {
                        "mime_type": "image/jpeg",
                        "data": screenshot_b64
                    }}
                ]
            }
        ]
    )
    
    return parse_response(response.text)