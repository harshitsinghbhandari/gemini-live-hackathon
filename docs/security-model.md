# Aegis Security Model: Graduated Trust

The core intellectual property of Aegis is its **Graduated Trust Security Model**. Instead of granting an AI agent blanket access to a system, Aegis introduces a dynamic trust boundary. Every proposed action is intercepted, analyzed, and classified into one of three risk tiers: **GREEN (Silent)**, **YELLOW (Confirm)**, or **RED (Biometric)**.

This classification is not based merely on the tool being used, but on the *intent* and the *irreversibility* of the action.

## 1. The Classifier Engine

The classification logic resides in `packages/aegis/agent/classifier.py`. It uses a dedicated, secondary LLM call (Gemini 2.5 Flash) separate from the main conversation stream.

Before any tool is executed, the `gate_action` function pauses the execution flow and asks the classifier to evaluate the intent.

The prompt is structured to ensure strict adherence to the tier rules, evaluating the "Selected tool" and "User intent" against a set of predefined security guidelines.

The classifier must output the tier, a reason for its decision, and what Aegis should say to the user before proceeding.

## 2. The Three Tiers (Irreversibility Criterion)

The defining metric for classification is **irreversibility**. Can the user easily undo this action if the AI hallucinates or misunderstands?

### 🟢 GREEN: Silent Execution (No Confirmation)
*   **Criterion:** The action is read-only, navigational, or purely informative. It cannot alter state in a meaningful or destructive way.
*   **Examples:** Opening an app, navigating to a URL, scrolling a page, reading screen text, taking a screenshot.
*   **Common Tools:** `navigation_tools`, `screen_tools.screen_capture`, `screen_tools.screen_read`.
*   **Execution:** Immediate and silent. Aegis behaves autonomously.

### 🟡 YELLOW: Verbal Confirmation Required
*   **Criterion:** The action mutates state or interacts with the UI in a way that *could* be unwanted, but is not critically destructive. It can usually be undone.
*   **Examples:** Clicking a "Sign In" button, typing a draft message, liking a post, creating a new folder.
*   **Common Tools:** `cursor_tools.cursor_click`, `cursor_tools.cursor_drag`, `keyboard_tools.keyboard_type`.
*   *(Exception: If a click is purely navigational, the classifier can downgrade it to GREEN).*
*   **Execution:** Aegis pauses, explains its intent ("I am about to click 'Submit'"), and waits for the user to verbally say "Yes" or "Proceed" over the audio stream.

### 🔴 RED: Biometric Authentication Required
*   **Criterion:** The action is highly sensitive, destructive, or irreversible. It involves financial data, security settings, or sending communications on the user's behalf.
*   **Examples:** Deleting files permanently, sending an email, merging a PR, revealing a password.
*   **Common Tools:** `keyboard_tools.keyboard_type_sensitive`, or any tool where the intent is destructive.
*   **Execution:** Execution is hard-blocked. An out-of-band request is generated and sent to the cloud backend. The user must authenticate using Face ID on their mobile app or Touch ID natively on the Mac.

## 3. Concrete Examples

| App / Context | Action | Classifier Tier | Why? |
| :--- | :--- | :--- | :--- |
| **Finder** | *"Open my Downloads folder."* | **GREEN** | Navigational. No state change. |
| **Notes** | *"Create a new note titled 'Ideas'."* | **YELLOW** | State change (creation), but easily reversible. |
| **Terminal** | *"Delete all files in the tmp folder."* | **RED** | Destructive and irreversible. |
| **Email** | *"Draft a reply to John."* | **YELLOW** | State change, but only a draft. |
| **Email** | *"Send the email to John."* | **RED** | Irreversible communication. |

## 4. The Fallback Mechanism

If the classifier fails to parse the response or encounters an error, Aegis employs a strict **fail-secure** architecture. Any uncertainty automatically escalates the action to RED, ensuring that bugs or hallucinations cannot bypass the trust boundary.

## 5. Implementation Reference
- Classifier: `packages/aegis/agent/classifier.py`
- Gatekeeper: `packages/aegis/agent/gate.py`
- Local Auth: `packages/aegis/auth.py`
boundary.