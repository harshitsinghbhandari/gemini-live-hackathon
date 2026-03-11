# Architectural Suggestions for Multimodal Performance

To reduce latency and improve the responsiveness of Aegis's multimodal capabilities, I suggest the following architectural and implementation changes, drawing from patterns observed in the GenMedia Live system.

---

## 1. Move to "Pseudo-Video" Continuous Stream
**Current Pattern**: Aegis captures a screenshot *reactively* after a tool call completes. This adds the capture/encode/upload time to the critical path of the model's next turn.
**Suggestion**: Implement a background polling loop (similar to GenMedia's `sender_loop` for camera frames) that sends low-resolution screenshots every 1.5–2 seconds using the `video` part of the Realtime API's `send_realtime_input`.
- **Benefit**: Gemini’s "visual context" is always fresh. By the time a tool finishes, Gemini may already have seen the result in the background stream, allowing for a faster response.

---

## 2. Optimize Image Encoding & Resampling
**Current Implementation**: `capture_screen` uses `Image.LANCZOS` for resizing, which is computationally expensive.
**Suggestion**:
- **Faster Filter**: Switch from `Image.LANCZOS` to `Image.BILINEAR`. In high-DPI desktop scenarios, the difference in quality is negligible for AI vision, but the speedup is significant.
- **JPEG Quality**: Lower JPEG quality to 60-70. GenMedia uses 60% for camera frames to minimize payload size.
- **Square Padding**: Gemini often processes 1:1 aspect ratio images more efficiently. Padding the 1470x956 screen to a square (e.g., 1024x1024) before sending can improve model accuracy and focus.

---

## 3. Parallelize Execution and Feedback
**Current Flow**: `Execute Tool` -> `Wait` -> `Capture Screenshot` -> `Send to Gemini`.
**Suggestion**:
- **Immediate Capture**: Fire the screenshot capture *concurrently* with the tool's final status check or security audit logging.
- **Pipelined Responses**: If the API supports it, send the `FunctionResponse` immediately, and follow up with a `Part` containing the image in a separate message turn if it helps reduce the "Time to First Token" (TTFT).

---

## 4. Delta-Based Screenshot Capture
**Idea**: To save bandwidth and processing, implement a simple pixel-hash check or "Dirty Region" detection.
- **Implementation**: Only send a new screenshot if the screen has changed significantly since the last 2-second poll. This reduces the number of tokens Gemini has to process in its context window, keeping the session "snappier" over time.

---

## 5. Tiered Quality Strategy
**Idea**: Adapt the screenshot quality based on the action type.
- **GREEN Actions (Read-only)**: Send high-res (LANCZOS, 90 quality) only when Gemini explicitly calls `screen_read`.
- **YELLOW/RED Actions (Control)**: Use low-res (BILINEAR, 60 quality) for rapid feedback during multi-step tasks like typing or clicking through a menu.

---

## Implementation Reference (Pattern from GenMedia)
In GenMedia Live, the `sender_loop` handles a queue of different multimodal types (audio, video, image, text). Aegis could adopt this "Bridge" pattern:
```python
# Draft pattern for AegisVoiceAgent
async def _visual_stream_loop(self, session):
    while self.is_active:
        shot = capture_screen(scale_to=(768, 768), filter=BILINEAR)
        await session.send_realtime_input(
            video=types.Blob(data=shot["base64"], mime_type="image/jpeg")
        )
        await asyncio.sleep(2.0)
```
This keeps the model "engaged" without blocking the main interaction loop.
w