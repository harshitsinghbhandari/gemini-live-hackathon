# Aegis: From Reactive to Autonomous

This document synthesizes the vision for the next evolution of Aegis, transitioning from a reactive tool-executor to a truly autonomous, closed-loop agent.

## Vision

The core shift is from **Blind Execution** (hoping an action worked) to **Closed-Loop Verification** (knowing it worked). The future Aegis is a **Hierarchical Multi-Agent System** where strategic planning is decoupled from high-speed execution, and every action is visually audited before the agent considers it "done."

### The Multi-Agent Hierarchy
*   **The Strategist (Gemini 3.1 Pro)**: Acts as the "Architect." It possesses global context, creates multi-step plans with explicit success criteria, and performs deep visual verification of critical states.
*   **The Operator (Gemini 2.5 Flash)**: Acts as the "Hands & Eyes." It handles the high-frequency live stream, executes discrete tools with precision timing, and performs immediate local verification (Look-Backs).

---

## Functional Requirements

### 1. Context-Aware "Foveated" Vision
The agent should move away from constant full-desktop streaming to reduce noise and hallucination.
*   **Active Window Tracking**: Automatically detect and focus on the bounds of the frontmost application.
*   **Visual Delta Triggering**: Only send visual updates to the model when the pixels within the active window change (e.g., >5% change).
*   **Anchored Cropping**: Send crops of the active window plus a 50px buffer to provide spatial context without full-screen bloat.
*   **On-Demand High-Res**: Provide a specific tool for the model to request a raw, uncompressed snapshot when local context is insufficient.

### 2. Serialized Closed-Loop Execution
Execution must move from batch processing to a self-correcting serial pipeline.
*   **Serial Multi-Execute**: Tools must be executed one-by-one with a mandatory "settling delay" (e.g., 200ms) to allow the UI to update.
*   **Immediate Look-Back**: After every click or type, the system must capture a local thumbnail (e.g., 100x100) of the interaction area to confirm the UI responded.
*   **Verification Checkpoints**: Every step in a multi-step plan must have a corresponding "Success State" check.

### 3. The "Anti-Liar" Protocol
Preventing the agent from hallucinating success is critical for trust.
*   **Speech Lock**: The Text-to-Speech (TTS) engine must be programmatically blocked from announcing completion ("Done," "Finished," "Sent") until a verification tool has returned a `SUCCESS` confirmation.
*   **Verification Gate**: If a checkpoint fails, execution stops immediately, and the agent must report the specific failure to the user rather than proceeding blindly.

---

## Success Criteria

### 1. Visual Grounding
*   The agent consistently clicks within the bounds of the intended UI element.
*   The "Red Circle" target is confirmed to be centered on the target element in the Verification Snapshot before a click is allowed.

### 2. Strategic Reliability
*   Complex tasks (e.g., "Message Harshit on WhatsApp") are broken down into logical steps with verifiable milestones.
*   The agent can autonomously detect when a plan step fails (e.g., a window didn't open) and triggers either a "Plan Correction" or a request for user assistance.

### 3. Efficiency & Cost
*   Visual token consumption is reduced by >50% through delta-based tracking and foveated cropping compared to continuous full-screen streaming.
*   Hallucination rates are minimized by providing high-density local context instead of low-density global context.
