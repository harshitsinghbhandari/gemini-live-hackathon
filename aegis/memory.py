"""
Aegis Memory System
Persistent user context that survives across sessions.
Stored locally in memory.json — never sent to backend.
"""
import json
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("aegis.memory")

MEMORY_PATH = Path(__file__).parent.parent / "memory.json"

DEFAULT_MEMORY = {
    "user": {
        "name": None,
        "timezone": None,
        "work_hours": None
    },
    "preferences": {
        "email_tone": "professional",
        "default_calendar": "primary",
        "default_task_list": "@default",
        "preferred_language": "English"
    },
    "context": {
        "current_projects": [],
        "github_username": None,
        "github_main_repo": None,
        "frequent_contacts": []
    },
    "learned": {
        "last_updated": None,
        "notes": []
    }
}

def load_memory() -> dict:
    """Load memory from disk. Creates default if missing."""
    if not MEMORY_PATH.exists():
        save_memory(DEFAULT_MEMORY)
        return DEFAULT_MEMORY.copy()
    try:
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load memory: {e}. Using defaults.")
        return DEFAULT_MEMORY.copy()

def save_memory(memory: dict):
    """Save memory to disk."""
    try:
        memory["learned"]["last_updated"] = datetime.now().isoformat()
        with open(MEMORY_PATH, "w") as f:
            json.dump(memory, f, indent=2)
    except Exception as e:
        logger.error(f"Could not save memory: {e}")

def memory_to_prompt(memory: dict) -> str:
    """Convert memory to natural language for Gemini system prompt."""
    lines = ["## What I know about you:"]

    user = memory.get("user", {})
    if user.get("name"):
        lines.append(f"- Your name is {user['name']}")
    if user.get("timezone"):
        lines.append(f"- Your timezone is {user['timezone']}")
    if user.get("work_hours"):
        lines.append(f"- You work {user['work_hours']}")

    prefs = memory.get("preferences", {})
    if prefs.get("email_tone"):
        lines.append(f"- You prefer {prefs['email_tone']} tone in emails")
    if prefs.get("default_task_list"):
        lines.append(f"- Your default task list ID is {prefs['default_task_list']}")
    if prefs.get("default_calendar"):
        lines.append(f"- Your default calendar is {prefs['default_calendar']}")

    ctx = memory.get("context", {})
    if ctx.get("current_projects"):
        lines.append(f"- Current projects: {', '.join(ctx['current_projects'])}")
    if ctx.get("github_username"):
        lines.append(f"- GitHub username: {ctx['github_username']}")
    if ctx.get("github_main_repo"):
        lines.append(f"- Main GitHub repo: {ctx['github_main_repo']}")
    if ctx.get("frequent_contacts"):
        contacts = ctx["frequent_contacts"]
        if contacts:
            lines.append(f"- Frequent contacts: {', '.join([c.get('name','') + ' (' + c.get('email','') + ')' for c in contacts])}")

    learned = memory.get("learned", {})
    if learned.get("notes"):
        lines.append("- Additional context:")
        for note in learned["notes"][-5:]:  # last 5 notes only
            lines.append(f"  • {note}")

    if len(lines) == 1:
        return ""  # No memory yet

    return "\n".join(lines)

async def update_memory_from_session(
    session_transcript: list,
    current_memory: dict,
    gemini_client
) -> dict:
    """
    After session ends, ask Gemini to extract anything new worth remembering.
    """
    if not session_transcript:
        return current_memory

    transcript_text = "\n".join(session_transcript[-20:])  # last 20 exchanges

    prompt = f"""
You are updating a user memory file for an AI agent.

Current memory:
{json.dumps(current_memory, indent=2)}

Session transcript (last 20 exchanges):
{transcript_text}

Extract ONLY new information worth remembering long-term:
- Names, emails of people mentioned
- User preferences expressed
- Projects or repos mentioned
- Corrections to existing memory
- Timezone or schedule info

Rules:
- Only update fields where new info was clearly stated
- Do NOT add speculation or assumptions
- Keep notes array under 20 items (remove oldest if needed)
- Return complete updated memory JSON only, nothing else
- If nothing new was learned, return current memory unchanged

Return updated memory JSON:
"""

    try:
        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        updated = json.loads(raw)
        save_memory(updated)
        logger.info("Memory updated from session")
        return updated
    except Exception as e:
        logger.warning(f"Memory update failed: {e}")
        return current_memory
