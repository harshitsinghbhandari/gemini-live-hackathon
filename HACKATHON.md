# Aegis: The Trusted Pilot for the Agentic Era

## The Problem
Autonomous AI agents are incredibly powerful, but they lack a fundamental concept: a **trust boundary**. Today's agents operate in a binary state: they are either entirely autonomous (which is terrifying when they have full access to your machine) or entirely manual (which defeats the purpose of an agent).

If you ask an AI to "summarize my emails," you want it to act quickly and silently. But if that same AI decides to "delete my repository" or "send a legally binding email," you want an immediate, hard stop. You want a way to say, *"Yes, I authorize this specific action."*

Without this trust boundary, users will never adopt true autonomous desktop agents. The risk is simply too high.

## The Core Insight: Graduated Trust
The solution is not to cripple the AI, but to introduce **Graduated Trust**. Aegis categorizes every proposed action into a three-tier security model:

*   🟢 **Silent (Green)**: Safe, read-only, or navigational actions (e.g., scrolling, reading screen text, clicking a link). These execute silently and instantly.
*   🟡 **Confirm (Yellow)**: State-mutating but non-destructive actions (e.g., typing an email draft, clicking "Submit"). These require verbal confirmation via the Gemini Live audio stream.
*   🔴 **Biometric (Red)**: Irreversible or highly sensitive actions (e.g., clicking "Send," entering passwords, deleting files). These trigger an out-of-band cryptographic challenge requiring Native Touch ID on the Mac or Face ID on a companion iPhone app (via WebAuthn).

This isn't just a heuristic; it's a fundamental architectural shift. Aegis evaluates the *irreversibility* of the intent, not just the tool being used.

## What Makes Aegis Different?
Every other agent submission focuses purely on *capability*—how many APIs they can connect, or how fast they can generate code. Aegis focuses on **safety and human-in-the-loop control**.

1.  **Native ComputerUse + Vision**: Aegis doesn't rely on brittle DOM scraping. It uses a high-speed duplex stream of audio and video with the Gemini Live API, streaming screenshots every few seconds, allowing it to "see" exactly what you see.
2.  **Out-of-Band Auth**: If the agent is compromised on the desktop, the authentication prompt is sent to a secondary device (your iPhone) via a WebSocket and Cloud Run backend. The Face ID approval is cryptographically signed and verified before the action executes.
3.  **Local-First, Cloud-Secured**: The agent runs locally on your Mac, ensuring screen data never unnecessarily leaves your machine except to the LLM. The cloud backend exists solely to broker secure biometric handshakes.

## Future Vision
Aegis is the foundation for an OS-level "Trust Gateway." In the future, operating systems won't just ask for microphone or camera permissions; they will ask for "Agentic Action" permissions based on risk tiers. Aegis demonstrates how this OS-level trust boundary will work, enabling humans to unleash AI agents on their personal computers without fear of irreversible mistakes.
