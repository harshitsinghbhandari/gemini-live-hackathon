# Aegis State-Gated Architecture

Aegis now follows a robust, state-gated orchestration model inspired by GenMedia. This architecture ensures strict synchronization between media streaming, reasoning, and tool execution, specifically preventing "Status 1008" (Policy Violation) errors.

## Unified State Management

The `AegisContext` now maintains a central `state` (defined in `aegis/context.py` as `SessionState` Enum):

1.  **LISTENING**: Default state. Hardware I/O (Microphone, Camera) is active. Gemini is ready for input.
2.  **THINKING**: Triggered as soon as server content (voice or thoughts) is detected. Media inputs are strictly gated (dropped) to respect the "Turn Gate."
3.  **EXECUTING**: Triggered during tool calls. All media streaming is paused. The agent waits for tool results before transitioning back.
4.  **DEAD**: Terminal state for the session.

## Components

### SessionBridge (voice.py)
The `SessionBridge` manages an `asyncio.Queue` for all outgoing messages to Gemini. This decouples hardware I/O loops from the high-speed Gemini WebSocket loop, preventing event loop blocking.

### Master Controller (voice.py)
The `receiver_loop` in `voice.py` acts as the Master Controller. It handles:
-   **State Transitions**: Real-time updates based on `server_content` and `turn_complete` signals.
-   **Session Resumption**: Capturing `new_handle` from `session_resumption_update` to allow seamless recovery from network disconnects.
-   **Tool Routing**: Intercepting `tool_call` requests and dispatching them to `gate_action`.

### Security & Visual Feedback
-   **Strict Gating**: `sender_loop` drops audio and video frames unless the state is explicitly `LISTENING`.
-   **Visual Feedback Loop**: Every `FunctionResponse` sent back to Gemini includes a fresh post-action screenshot to provide visual context of the action's result.
-   **Retina Scaling**: `aegis/computer_use.py` now applies a 2.0x multiplier to all coordinates to ensure pixel-perfect interaction on macOS Retina displays.

## Guidelines for Future Tasks
-   When adding new tools, ensure they are routed through `gate_action` to maintain security tiers.
-   Always use `context.state` to check the current orchestrator status.
-   Do not bypass the `SessionBridge` for communication with Gemini.
