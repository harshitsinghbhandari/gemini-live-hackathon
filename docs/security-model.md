# Aegis Security Model: Graduated Trust

The core intellectual property of Aegis is its **Graduated Trust Security Model**. Instead of granting an AI agent blanket access to a system, Aegis introduces a dynamic trust boundary. Every proposed action is intercepted, analyzed, and classified into one of three risk tiers: **GREEN (Silent)**, **YELLOW (Confirm)**, or **RED (Biometric)**.

This classification is not based merely on the tool being used, but on the *intent* and the *irreversibility* of the action.

## 1. The Classifier Engine

The classification logic resides in `packages/aegis/agent/classifier.py`. It uses a dedicated, secondary LLM call (Gemini 2.5 Flash) separate from the main conversation stream.

Before any tool is executed, the `gate_action` function pauses the execution flow and asks the classifier to evaluate the intent.

The prompt (defined in `configs/agent/prompts.yaml`) is structured strictly:
```yaml
CLASSIFY_WITH_HINT_PROMPT_TEMPLATE: |
  You are a security classifier for Aegis, an AI agent controlling a Mac.

  Selected tool: {tool_hint}
  User intent: {proposed_action}

  Tier rules:
  {tier_rules_summary}

  Respond ONLY with valid JSON...
```

The classifier must output the tier, a reason for its decision, and what Aegis should say to the user before proceeding.

## 2. The Three Tiers (Irreversibility Criterion)

The defining metric for classification is **irreversibility**. Can the user easily undo this action if the AI hallucinates or misunderstands?

### 🟢 GREEN: Silent Execution (No Confirmation)
*   **Criterion:** The action is read-only, navigational, or purely informative. It cannot alter state in a meaningful or destructive way.
*   **Examples:** Opening an app, navigating to a URL, scrolling a page, reading screen text, taking a screenshot.
*   **Tool Mapping:** `screen_capture`, `screen_read`, `cursor_move`, `browser_navigate`, `browser_read`, `keyboard_hotkey` (e.g., Command+Tab).
*   **Execution:** Immediate and silent. Aegis behaves autonomously.

### 🟡 YELLOW: Verbal Confirmation Required
*   **Criterion:** The action mutates state or interacts with the UI in a way that *could* be unwanted, but is not critically destructive. It can usually be undone (e.g., deleting a character in a text box, clicking a non-committal button).
*   **Examples:** Clicking a "Sign In" button (assuming credentials are auto-filled), typing a draft message into a text field, liking a post.
*   **Tool Mapping:** `cursor_click`, `cursor_drag`, `keyboard_type`, `browser_click`, `browser_type`.
*   *(Exception: If a click is purely navigational, like clicking a search result link, the classifier is instructed to downgrade it to GREEN).*
*   **Execution:** Aegis pauses, explains its intent ("I am about to click 'Submit'"), and waits for the user to verbally say "Yes" or "Proceed" over the audio stream.

### 🔴 RED: Biometric Authentication Required
*   **Criterion:** The action is highly sensitive, destructive, or irreversible. It involves financial data, security settings, or sending communications on the user's behalf.
*   **Examples:** Deleting files permanently (`rm -rf`), sending an email, transferring funds, revealing a saved password.
*   **Tool Mapping:** `keyboard_type_sensitive` (a specialized tool for entering critical data), or any standard tool (`cursor_click`) if the intent is classified as destructive (e.g., clicking the final "Send" button on an email).
*   **Execution:** Execution is hard-blocked. An out-of-band request is generated and sent to the cloud backend. The user must physically authenticate using Face ID on their companion mobile app (or Touch ID on the Mac natively).

## 3. Concrete Examples

Let's look at how the same underlying task (interacting with Gmail or GitHub) escalates through the tiers based on the specific action.

| App / Context | Action | Classifier Tier | Why? |
| :--- | :--- | :--- | :--- |
| **GitHub** | *"Aegis, open my pull requests."* | **GREEN** | Purely navigational. `browser_navigate` or `cursor_click`. Undoing is just clicking 'Back'. |
| **GitHub** | *"Aegis, write a comment saying 'LGTM'."* | **YELLOW** | State mutating. `browser_type`. The comment is drafted, but usually requires a separate click to post. Aegis asks for voice confirmation before typing. |
| **GitHub** | *"Aegis, merge this pull request."* | **RED** | Irreversible (or difficult to reverse) and highly impactful. Even if using a simple `cursor_click` on the "Merge" button, the intent triggers a Face ID challenge. |
| **Gmail** | *"Aegis, read the subject of the latest email."* | **GREEN** | Read-only. `screen_read`. No harm possible. |
| **Gmail** | *"Aegis, draft a reply saying I'll be late."* | **YELLOW** | State mutating. `keyboard_type`. Creates a draft but does not send it. |
| **Gmail** | *"Aegis, send the email."* | **RED** | Irreversible. Sending communication on behalf of the user is the highest risk action. Requires Face ID. |

## 4. The Fallback Mechanism

If the classifier fails to parse the Gemini response, or if the API times out, Aegis employs a strict **fail-secure** architecture.

```python
# packages/aegis/agent/classifier.py
if not classification:
    # Fallback to safe state
    return {"tier": "RED", "reason": "Failed to parse classification", "upgraded": True, "speak": "I encountered an error and must block this action for safety.", "tool": None, "arguments": {}}
```
Any uncertainty automatically escalates the action to RED, ensuring that bugs or hallucinations cannot bypass the trust boundary.