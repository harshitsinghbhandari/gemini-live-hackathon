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

TIER RULES FOR NEW TOOLKITS:
- GREEN (read-only): listing tasks, reading docs, viewing sheets, getting presentations, listing GitHub issues/PRs
- YELLOW (creates/modifies): creating docs, adding rows to sheets, creating presentations, adding tasks, creating GitHub issues
- RED (irreversible): deleting docs, clearing sheets, deleting tasks, merging PRs, deleting repositories

TOOLKIT REFERENCE — use these exact tool names:

=== GMAIL (already exists) ===
GREEN: GMAIL_FETCH_EMAILS, GMAIL_LIST_THREADS, GMAIL_GET_ATTACHMENT
YELLOW: GMAIL_CREATE_EMAIL_DRAFT, GMAIL_REPLY_TO_THREAD
RED: GMAIL_SEND_EMAIL, GMAIL_DELETE_MESSAGE, GMAIL_TRASH_EMAIL

=== GOOGLE CALENDAR (already exists) ===
GREEN: GOOGLECALENDAR_LIST_EVENTS, GOOGLECALENDAR_GET_EVENT
YELLOW: GOOGLECALENDAR_CREATE_EVENT, GOOGLECALENDAR_UPDATE_EVENT
RED: GOOGLECALENDAR_DELETE_EVENT

=== GOOGLE DOCS ===
GREEN: GOOGLEDOCS_GET_DOCUMENT_BY_ID
YELLOW: GOOGLEDOCS_CREATE_DOCUMENT, GOOGLEDOCS_CREATE_DOCUMENT_MARKDOWN
RED: GOOGLEDOCS_DELETE_CONTENT_RANGE, GOOGLEDOCS_DELETE_TABLE, GOOGLEDOCS_EXPORT_DOCUMENT_AS_PDF

=== GOOGLE SHEETS ===
GREEN: GOOGLESHEETS_GET_BATCH_VALUES, GOOGLESHEETS_FIND_WORKSHEET_BY_TITLE, GOOGLESHEETS_AGGREGATE_COLUMN_DATA
YELLOW: GOOGLESHEETS_CREATE_GOOGLE_SHEET1, GOOGLESHEETS_CREATE_SPREADSHEET_ROW, GOOGLESHEETS_CREATE_SPREADSHEET_COLUMN, GOOGLESHEETS_BATCH_UPDATE, GOOGLESHEETS_FORMAT_CELL
RED: GOOGLESHEETS_DELETE_SHEET, GOOGLESHEETS_DELETE_DIMENSION, GOOGLESHEETS_CLEAR_VALUES

=== GOOGLE SLIDES ===
GREEN: GOOGLESLIDES_PRESENTATIONS_GET, GOOGLESLIDES_PRESENTATIONS_PAGES_GET
YELLOW: GOOGLESLIDES_CREATE_PRESENTATION, GOOGLESLIDES_CREATE_SLIDES_MARKDOWN, GOOGLESLIDES_PRESENTATIONS_COPY_FROM_TEMPLATE
RED: GOOGLESLIDES_PRESENTATIONS_BATCH_UPDATE

=== GOOGLE TASKS ===
GREEN: GOOGLETASKS_LIST_ALL_TASKS, GOOGLETASKS_LIST_TASKS, GOOGLETASKS_GET_TASK, GOOGLETASKS_LIST_TASK_LISTS
YELLOW: GOOGLETASKS_INSERT_TASK, GOOGLETASKS_BULK_INSERT_TASKS, GOOGLETASKS_CREATE_TASK_LIST, GOOGLETASKS_UPDATE_TASK
RED: GOOGLETASKS_DELETE_TASK, GOOGLETASKS_DELETE_TASK_LIST, GOOGLETASKS_CLEAR_TASKS

=== GITHUB ===
GREEN: GITHUB_LIST_REPOSITORY_ISSUES, GITHUB_GET_AN_ISSUE, GITHUB_LIST_PULL_REQUESTS, GITHUB_GET_A_PULL_REQUEST, GITHUB_LIST_COMMITS
YELLOW: GITHUB_CREATE_AN_ISSUE, GITHUB_ADD_ASSIGNEES_TO_AN_ISSUE, GITHUB_ADD_LABELS_TO_AN_ISSUE, GITHUB_CREATE_A_PULL_REQUEST_REVIEW
RED: GITHUB_DELETE_A_REPOSITORY, GITHUB_MERGE_A_PULL_REQUEST

EXAMPLES:
"create a doc about meeting notes" → GOOGLEDOCS_CREATE_DOCUMENT_MARKDOWN, YELLOW
"read my spreadsheet" → GOOGLESHEETS_GET_BATCH_VALUES, GREEN
"add a row to my budget sheet" → GOOGLESHEETS_CREATE_SPREADSHEET_ROW, YELLOW
"make a presentation about Q4 results" → GOOGLESLIDES_CREATE_SLIDES_MARKDOWN, YELLOW
"add buy groceries to my tasks" → GOOGLETASKS_INSERT_TASK, YELLOW
"what are my tasks today" → GOOGLETASKS_LIST_ALL_TASKS, GREEN
"create a github issue for this bug" → GITHUB_CREATE_AN_ISSUE, YELLOW
"show me open PRs" → GITHUB_LIST_PULL_REQUESTS, GREEN
"merge this PR" → GITHUB_MERGE_A_PULL_REQUEST, RED
"delete this task list" → GOOGLETASKS_DELETE_TASK_LIST, RED

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
