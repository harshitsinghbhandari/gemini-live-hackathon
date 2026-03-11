# Gemini Live API Migration Guide

Aegis has transitioned from a standard text-based agent to a fully multimodal agent powered by the Gemini Live API (`gemini-2.5-flash-native-audio-latest`).

## Key Changes

### 1. Duplex Multimodal Streaming
Aegis now uses a persistent WebSocket connection to stream both Audio (Mic) and Video (Screenshots) simultaneously. This enables real-time "Vision" where the agent can see what you are doing as you talk.

### 2. State Machine Logic
To manage the high-speed stream, we implemented a custom state machine in `aegis/context.py`. This ensures that media packets are dropped when the model is already executing a tool, preventing the common `1008` (Policy Violation) errors in the Live SDK.

### 3. Native ComputerUse
We moved away from Composio and other external tool routers. Aegis now defines its own `ComputerUse` schemas directly in `aegis/screen_executor.py`, providing lower latency and tighter security integration.

### 4. ThinkingConfig & Thoughts
Aegis enables `ThinkingConfig(include_thoughts=True)`. This allows the UI to display the agent's internal reasoning ("Thoughts") in real-time via the `thought` WebSocket event, providing transparency into the agent's decision-making process.

## Migration Path for Developers

If you are upgrading an older version of Aegis:
1.  **Dependencies**: Install `google-genai` and `mss`.
2.  **Environment**: Ensure `GOOGLE_API_KEY` supports Gemini 2.5.
3.  **Entry Point**: Start the agent via `main.py` which initializes the `AegisVoiceAgent` with the new Live configuration.
