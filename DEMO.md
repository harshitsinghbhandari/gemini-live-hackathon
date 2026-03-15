# Aegis Demo Guide for Judges

Welcome to the Aegis Demo! This guide is designed to help you experience the core value proposition of Aegis: **Graduated Trust in Autonomous Agents**.

Aegis is not just a chatbot; it's a "Trusted Pilot" for your Mac that enforces a strict security boundary by classifying every action into three risk tiers: Silent (Green), Confirm (Yellow), and Biometric (Red).

By following these steps, you will see how Aegis balances autonomy with safety.

---

## Prerequisites
Before you begin the demo, please ensure the following:

1.  **Local Agent Running:** The Python agent and helper server must be running. You should see local ports `8765` and `8766` active in your terminal.
2.  **Mac PWA Open:** The primary interface should be open in a browser (`https://aegismac.projectalpha.in`). The interface should show the **Listening** state.
3.  **Mobile Companion App Installed:** You must have the Aegis Companion App installed as a PWA on your iPhone (`https://aegismobile.projectalpha.in`) and have completed the **Register Face ID** step.
4.  **Dashboard Open:** Keep the Dashboard (`https://aegisdashboard.projectalpha.in`) open on a secondary monitor or split-screen to watch the real-time Server-Sent Events (SSE) audit log.

---

## Demo Script

### 1. The GREEN Action (Silent Execution)
Green actions are safe, read-only, or navigational actions. They execute silently and instantly, demonstrating Aegis's autonomy.

*   **You say:** *"Aegis, take a screenshot and tell me what the top headline is on the current webpage."*
*   **What to expect on your Mac:**
    *   Aegis will transition to the `THINKING` state.
    *   It will execute a `screen_capture` or `screen_read` tool silently.
    *   Aegis will respond verbally with the information.
*   **What to expect on the Dashboard:**
    *   A new log entry will appear with a green badge: `[GREEN] Action: Read screen | Tool: screen_read`

### 2. The YELLOW Action (Voice Confirmation)
Yellow actions are state-mutating but non-destructive (e.g., clicking a non-critical button, typing a draft). They require explicit verbal confirmation.

*   **You say:** *"Aegis, click the 'Sign In' button on the top right."*
*   **What to expect on your Mac:**
    *   Aegis will transition to the `THINKING` state.
    *   Instead of immediately executing the click, Aegis will pause and ask you: *"I am about to click the 'Sign In' button. Is that okay?"*
*   **You reply:** *"Yes, proceed."*
*   **What happens next:**
    *   Aegis executes the `cursor_click` (or `click_by_word`) tool. You will see your mouse cursor move and click the button.
*   **What to expect on the Dashboard:**
    *   A log entry will appear with a yellow badge: `[YELLOW] Action: Click Sign In | Tool: cursor_click | Confirmed: True`

### 3. The RED Action (Biometric Authentication)
Red actions are irreversible, destructive, or highly sensitive (e.g., sending an email, deleting a file). These *cannot* be authorized by voice alone; they require an out-of-band biometric challenge.

*   **You say:** *"Aegis, open Terminal and forcefully delete the `downloads` folder."* (Or any similar destructive command using `keyboard_type_sensitive`).
*   **What to expect on your Mac:**
    *   Aegis transitions to the `THINKING` state.
    *   Aegis will say: *"This action requires biometric authentication. Please check your mobile device."*
    *   The Mac PWA will display a "Waiting for Authentication" prompt, showing a crop of the screen where the action is proposed.
*   **What to expect on your iPhone:**
    *   The Aegis Mobile App will display an **Auth Request**.
    *   It will show the proposed action ("Delete downloads folder") and the requested tool (`keyboard_type_sensitive`).
    *   You must tap "Approve."
    *   Face ID (or Touch ID) will prompt you for cryptographic verification via WebAuthn.
*   **What happens next:**
    *   Once Face ID succeeds, the iPhone sends the signed payload to the Cloud Run backend.
    *   The backend validates the signature and updates the Firestore document.
    *   The local Mac agent, polling the backend, sees the approval and immediately executes the action.
*   **What to expect on the Dashboard:**
    *   A log entry will appear with a red badge: `[RED] Action: Delete downloads | Tool: keyboard_type_sensitive | Auth_Used: True`

---

## Known Limitations & Sandbox Notes

While reviewing Aegis, please keep the following in mind:

*   **Local Screen Context:** Aegis uses the Gemini Live API for voice interaction but relies on `mss` (a fast, cross-platform screenshot library) and `pyautogui` for execution, rather than sending continuous, raw desktop streams to the cloud. This hybrid approach saves massive bandwidth but means Aegis sometimes needs to "look closely" (`screen_crop`) to find exact clickable coordinates.
*   **Pure Native Control:** Aegis relies entirely on a **Native ComputerUse** model (visual processing + native clicks/typing). This is far more secure and realistic for a general-purpose agent than brittle third-party API integrations.