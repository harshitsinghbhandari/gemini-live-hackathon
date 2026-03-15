# Legacy: Composio Toolkits Integration

*Note: As of tag `v2.7.0`, Aegis pivoted away from Composio in favor of Native ComputerUse (vision + `pyautogui`). However, this document preserves the architecture and reasoning behind the original 7 toolkits used during the `v1.7.1` milestone, as they perfectly illustrate the Graduated Trust Security Model applied to APIs.*

During its initial development, Aegis integrated with **Composio**, a platform that provides unified toolkits for connecting AI agents to third-party services. Aegis utilized 7 core toolkits:

1.  **Gmail**
2.  **Google Calendar**
3.  **Google Docs**
4.  **Google Sheets**
5.  **Google Slides**
6.  **Google Tasks**
7.  **GitHub**

## The Tier Mapping Logic

Even when using API calls instead of screen clicks, Aegis enforced the Three-Tier Security Model. The classifier (`packages/aegis/agent/classifier.py` in older commits) intercepted the `composio_execute` tool call, evaluated the *intent* of the specific action within the toolkit, and assigned a risk tier.

Here is how the 7 toolkits and their actions mapped to the tiers:

### 🟢 GREEN (Silent Execution)
**Criteria:** The API call is `GET` or purely read-only. It fetches data but alters nothing on the server.

*   **Gmail:** `GMAIL_GET_MESSAGE`, `GMAIL_LIST_THREADS`, `GMAIL_SEARCH`
*   **Calendar:** `CALENDAR_GET_EVENT`, `CALENDAR_LIST_EVENTS`
*   **Docs/Sheets/Slides:** `GOOGLE_DOCS_READ`, `GOOGLE_SHEETS_GET_VALUES`
*   **Tasks:** `GOOGLE_TASKS_LIST`
*   **GitHub:** `GITHUB_GET_REPO`, `GITHUB_LIST_ISSUES`, `GITHUB_GET_PULL_REQUEST`

**Why?** Reading a calendar event or viewing a GitHub issue poses no risk of data loss or unauthorized communication. Aegis could execute these autonomously without interrupting the user.

### 🟡 YELLOW (Voice Confirmation)
**Criteria:** The API call is a `POST`/`PUT`/`PATCH` that mutates state, but the impact is internal, non-destructive, or easily reversible.

*   **Gmail:** `GMAIL_CREATE_DRAFT` (Creating a draft doesn't send it, so it's safe but mutates state).
*   **Calendar:** `CALENDAR_CREATE_EVENT`, `CALENDAR_UPDATE_EVENT`
*   **Docs/Sheets/Slides:** `GOOGLE_DOCS_CREATE`, `GOOGLE_SHEETS_UPDATE_VALUES`
*   **Tasks:** `GOOGLE_TASKS_INSERT`, `GOOGLE_TASKS_UPDATE`
*   **GitHub:** `GITHUB_CREATE_ISSUE`, `GITHUB_ISSUE_COMMENT`

**Why?** Creating a calendar event or drafting an email changes the user's data. Aegis requires the user to say "Yes, proceed" before making the API call to ensure it hasn't hallucinated a meeting time or issue description.

### 🔴 RED (Biometric Authentication)
**Criteria:** The API call is highly sensitive, sends communication to external parties, or is destructive (`DELETE`).

*   **Gmail:** `GMAIL_SEND_MESSAGE`, `GMAIL_TRASH_MESSAGE`
*   **Calendar:** `CALENDAR_DELETE_EVENT`
*   **GitHub:** `GITHUB_MERGE_PULL_REQUEST`, `GITHUB_DELETE_REPO`

**Why?** Sending an email cannot be undone. Merging a PR affects a codebase permanently. Deleting an event might confuse invitees. These actions were hard-blocked and triggered an out-of-band Face ID challenge on the companion mobile app.

## Why We Moved Away from Composio

While the mapping above worked perfectly to demonstrate the security model, it had limitations for a truly general-purpose desktop agent:

1.  **OAuth Friction:** Users had to authenticate Composio with every individual service (Google, GitHub, Slack, etc.).
2.  **Google App Verification:** As an unverified app, getting read access to Gmail via OAuth is nearly impossible for non-test users.
3.  **Visual Grounding:** When an agent uses an API in the background, the user doesn't see what's happening on their screen. This breaks trust.

By moving to **Native ComputerUse** (vision + native cursor clicks), Aegis now bypasses OAuth entirely. It interacts with the web browser exactly like a human does, providing visual proof of its actions while still strictly enforcing the GREEN/YELLOW/RED trust boundaries.