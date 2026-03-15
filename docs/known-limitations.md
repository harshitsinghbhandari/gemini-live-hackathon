# Aegis: Known Limitations

Aegis is a functional prototype built for the Gemini Live Agent Challenge. While it successfully demonstrates the core concept of a three-tier security model (Graduated Trust), there are several known limitations due to the nature of the hackathon sandbox and evolving architectural decisions.

## 1. Google OAuth Restrictions (Gmail & Drive)
**Limitation:** When attempting to use Aegis to read emails via Gmail, the action may fail or be blocked by Google's OAuth consent screen.
**Reason:** This is a Google policy, not a bug in Aegis. The Aegis GCP project is currently "unverified." Google enforces strict restrictions on unverified apps requesting sensitive scopes (like `https://www.googleapis.com/auth/gmail.readonly`). Only explicitly whitelisted test accounts can grant these permissions.
**Roadmap:** For a production release, the Aegis application would need to undergo a formal security audit and verification process by Google to remove this restriction for general users.

## 2. The Shift from Composio to Native ComputerUse
**Limitation:** The repository contains documentation (and git history) referencing "7 Composio Toolkits" (Gmail, Calendar, Docs, Sheets, Slides, Tasks, GitHub). However, the current active deployment no longer relies on Composio.
**Reason:** We pivoted from third-party API integrations (Composio) to **Native ComputerUse** (using Gemini's vision capabilities combined with local `pyautogui` and OCR).
*   **Why?** True agentic trust requires the agent to see what the user sees and interact with the UI directly. Relying on background API calls bypasses the visual verification step crucial for user trust. Furthermore, Native ComputerUse allows Aegis to control *any* application on the Mac, not just those with pre-built API integrations.
**Roadmap:** We plan to refine the native execution engine, improving the reliability of `click_by_word` and visual element grounding, making third-party API wrappers entirely obsolete for basic desktop navigation.

## 3. PWA vs. Native iOS Companion App
**Limitation:** The mobile companion app (used for Face ID / RED tier authentication) is built as a Progressive Web App (PWA) rather than a native iOS app distributed via the App Store.
**Reason:** PWAs allow for rapid, cross-platform deployment during a hackathon without the delays of App Store review. WebAuthn is fully supported in mobile Safari, allowing us to leverage the device's secure enclave (Face ID) perfectly.
**Roadmap:** A native iOS app is planned. A native app can receive silent Apple Push Notifications (APNs) faster than a PWA polling a backend, reducing the latency between a RED action being proposed on the Mac and the Face ID prompt appearing on the iPhone.

## 4. Mac Accessibility Permissions
**Limitation:** Aegis requires extensive macOS Accessibility and Screen Recording permissions to function. If these are revoked or not granted correctly during setup, the agent cannot see or click.
**Reason:** This is fundamental to how Native ComputerUse works on macOS.
**Roadmap:** In a true OS-level integration (the ultimate vision for Aegis), the agent would be a trusted system daemon, and these permissions would be managed via a dedicated "Agentic Trust" preference pane rather than general accessibility settings.

## 5. Vision Token Latency
**Limitation:** Sending continuous high-resolution screenshots to the Gemini Live API consumes significant bandwidth and tokens, and introduces latency before the agent can react to visual changes.
**Reason:** The architecture currently relies heavily on the cloud LLM to interpret the screen.
**Roadmap:** We plan to move more visual processing (like basic element detection and bounding box extraction) to lightweight, local on-device models, using the large cloud LLM only for complex reasoning and planning. This will drastically reduce latency and token usage.