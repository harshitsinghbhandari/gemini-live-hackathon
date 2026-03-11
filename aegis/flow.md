# Aegis Multimodal Flow Documentation

This document traces the exact execution path from user input to screen action.

---

## 1. Input: Audio & Video Stream
Aegis maintains two continuous outbound streams to Gemini Live.

- **Audio Capture**: `voice.py` -> `_send_audio_loop` captures PCM audio at 16kHz.
- **Vision Capture**: `voice.py` -> `_visual_stream_loop` captures screenshots using `mss`. It uses delta-based change detection (MD5 hashing) to only send frames when the screen changes, optimizing bandwidth.
- **State Check**: Media is only sent when the state machine is in `LISTENING`.

---

## 2. Processing: Gemini Live API
Gemini processes the multimodal stream and responds in real-time.

- **Barge-in**: Handled natively by Gemini Live; Aegis UI reflects this via WebSocket events.
- **Thought Streaming**: Gemini's internal reasoning is captured via `ThinkingConfig` and broadcast to the dashboard.

---

## 3. Decision: Tool Call Interception
When Gemini decides to act, it issues a `tool_call`.

- **Detection**: `voice.py` -> `_receive_and_play_loop` detects the `tool_call`.
- **State Transition**: Immediately transitions state to `EXECUTING` and purges pending media to prevent policy violations (1008).

---

## 4. Security: The Aegis Gate
Every action is audited and gated by `gate.py`.

- **Classification**: `classifier.py` uses Gemini 2.5 Flash to assign a tier (GREEN/YELLOW/RED).
- **Authorization**:
    - **GREEN**: Logged and executed.
    - **YELLOW**: Agent asks "Should I proceed?" verbally.
    - **RED**: Agent triggers macOS Touch ID or sends an FCM notification to the mobile app for Face ID.

---

## 5. Execution: Native ComputerUse
Once authorized, the action is dispatched to `screen_executor.py`.

- **Normalization**: Coordinates are denormalized from Gemini's 0-1000 scale to physical pixels.
- **Precision**:
    - `cursor_target` places a red circle.
    - `screen_crop` provides high-res zoom for small elements.
- **Automation**: `pyautogui` executes the click, drag, or keypress.

---

## 6. Feedback: Context Refresh
After execution, the loop closes.

- **Snapshot**: A "Verification Snapshot" is taken after the tool runs.
- **Return**: The result and the snapshot are sent back to Gemini as a `FunctionResponse`.
- **Resume**: State transitions back to `LISTENING`.
