# Native ComputerUse Integration

Aegis uses native ComputerUse as its primary interface for controlling the macOS desktop. This bypasses high-latency cloud tool providers in favor of direct, OS-level manipulation.

## Core Architecture

The integration follows a three-layer model:

1.  **Orchestration (`voice.py`)**: Manages the Gemini Live session and sends continuous screen updates.
2.  **Gateway (`gate.py`)**: Enforces the 3-tier security model (GREEN/YELLOW/RED) on every proposed screen action.
3.  **Execution (`screen_executor.py`)**: Dispatches the authorized action to low-level drivers.

## Precision Control Tools

Aegis extends basic click/type capabilities with precision tools:

- **`screen_capture`**: Full-screen view.
- **`screen_crop`**: High-resolution zoom on a Region of Interest (ROI).
- **`cursor_target`**: Places a red overlay on the target element for visual verification.
- **`cursor_confirm_click`**: Executes the click only after the target is verified.
- **`cursor_nudge`**: Fine-grained pixel adjustments (e.g., "Move 5 pixels left").

## State Machine Coordination

ComputerUse actions are coordinated via a state machine in `context.py`:

- **`LISTENING`**: Mic and Vision active.
- **`THINKING`**: Gemini is processing the vision/audio stream.
- **`EXECUTING`**: A tool call has been intercepted. Media streaming is paused to prevent 1008 policy violations.
- **`BUSY`**: Agent is performing an action (e.g., waiting for Touch ID).

## Security Mapping

Every ComputerUse tool is mapped to a risk tier:

| Tool | Tier | Reason |
| --- | --- | --- |
| `screen_capture` | GREEN | Read-only |
| `cursor_move` | GREEN | Non-destructive |
| `cursor_click` | YELLOW | Modifies UI state |
| `keyboard_type` | YELLOW | Inputs data |
| `keyboard_type_sensitive`| RED | Potential credential exposure |
