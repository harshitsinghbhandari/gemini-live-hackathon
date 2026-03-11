# Multimodal Performance & Vision Optimizations

Aegis implements a "Vision-First" architecture using the Gemini Live API. This document outlines the optimizations already implemented and future suggestions for multimodal performance.

---

## 1. Implemented: Delta-Based Screenshot Streaming
**Pattern**: Aegis maintains a continuous background loop that sends screenshots via the `video` parameter of `send_realtime_input`.
- **Optimization**: We use MD5 hashing to detect changes in the screen state. Frames are only transmitted if the screen content has changed since the last poll (1.0s interval), significantly reducing token consumption and bandwidth.
- **State Integration**: The stream is tightly coupled with the state machine; frames are dropped during `THINKING` and `EXECUTING` states to prevent Gemini Live policy violations (1008).

---

## 2. Implemented: High-Resolution Crops (Foveated Vision)
**Pattern**: To balance bandwidth with accuracy, Aegis uses a "Foveated Vision" strategy.
- **Base Layer**: Standard background stream is medium resolution.
- **Precision Layer**: When Gemini needs to interact with a small element, it calls `screen_crop`. This captures a high-resolution, lossless crop of the specific Region of Interest (ROI), providing the model with the clarity needed for precision clicking.

---

## 3. Implemented: Verification Thumbnails
**Pattern**: For "RED" and "YELLOW" actions, Aegis provides visual feedback before execution.
- **Mechanism**: The `cursor_target` tool draws a red overlay and returns a 200x200 "Verification Snapshot" of the target area. This allows the model to "see" where it is about to click and correct its coordinates if necessary.

---

## 4. Suggestions: Parallelized Media Pipe
**Current Flow**: Audio and Video are sent sequentially in the hardware loops.
**Future Optimization**: Implement a multiplexed media pipe that prioritizes audio packets over video frames when bandwidth is constrained, ensuring that voice interaction remains fluid even during heavy screen updates.

---

## 5. Suggestions: Predictive Frame Capture
**Concept**: Capture a screenshot *immediately* upon detecting a tool call, before the gate logic finishes.
- **Benefit**: By the time the user provides Touch ID or verbal confirmation, the "post-action" screenshot is already being encoded, reducing the latency between auth-approval and the agent's next turn.
