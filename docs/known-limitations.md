# Aegis: Known Limitations

Aegis is a functional prototype built for the Gemini Live Agent Challenge. While it successfully demonstrates the core concept of a three-tier security model (Graduated Trust), there are several known limitations due to the nature of the hackathon sandbox and evolving architectural decisions.

## 1. Google OAuth Restrictions (Gmail & Drive)
**Limitation:** When attempting to use Aegis to read emails via Gmail, the action may fail or be blocked by Google's OAuth consent screen.
**Reason:** This is a Google policy, not a bug in Aegis. The Aegis GCP project is currently "unverified." Google enforces strict restrictions on unverified apps requesting sensitive scopes.
**Roadmap:** Production release requires formal security audit and verification by Google.

## 2. The Shift from Composio to Native ComputerUse
**Limitation:** The repository transition from background API integrations (Composio) to **Native ComputerUse**.
**Reason:** True agentic trust requires the agent to see what the user sees and interact with the UI directly. Native ComputerUse (using Gemini's vision + local `pyautogui`) allows Aegis to control *any* application on the Mac.
**Roadmap:** Refine the native execution engine, improving the reliability of visual element grounding and OCR.

## 3. PWA vs. Native iOS Companion App
**Limitation:** The mobile companion app is a PWA.
**Reason:** Rapid, cross-platform deployment during a hackathon. WebAuthn is fully supported in mobile Safari, allowing access to the device's secure enclave (Face ID).
**Roadmap:** Native iOS app is planned for faster, silent push notifications (APNs).

## 4. macOS Hardware & Permissions
**Limitation:** Aegis requires specific macOS hardware (for Touch ID) and extensive permissions (Accessibility, Screen Recording).
**Reason:** Native automation and biometric security rely on platform-specific frameworks like `LocalAuthentication` and `pyobjc`.
**Roadmap:** Move towards a trusted system daemon architecture for better permission management.

## 5. Vision Token Latency
**Limitation:** Continuous screenshot streaming consumes bandwidth and tokens, and introduces latency.
**Reason:** Heavy reliance on cloud LLM for visual interpretation.
**Roadmap:** Offload basic visual tasks (element detection, OCR) to local on-device models, using the cloud LLM only for high-level reasoning.