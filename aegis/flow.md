# Aegis Voice Flow Documentation

This document traces the exact execution path from the moment a user speaks to the completion of an action.

---

## 1. User Speaks (Audio Capture & Stream)
When the user speaks, the audio is captured via the microphone and streamed to the Gemini Live API.

- **Audio Capture Loop**: `aegis/voice.py` -> `AegisVoiceAgent._send_audio_loop`
- **Reading Chunk**: `data = await asyncio.to_thread(stream.read, config.CHUNK_SIZE, False)`
- **Broadcasting Waveform**: `ws_server.broadcast("waveform", value=round(peak, 3))`
- **Sending to Gemini**: `await session.send_realtime_input(audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={config.SEND_SAMPLE_RATE}"))`

---

## 2. Gemini Responds (Audio Playback & Tool Trigger)
Gemini processes the audio and responds with either audio (speech) or a tool call (action).

- **Reception Loop**: `aegis/voice.py` -> `AegisVoiceAgent._receive_and_play_loop`
- **Listening for Response**: `async for response in session.receive():`
- **Audio Playback**: `await asyncio.to_thread(output_stream.write, part.inline_data.data)`
- **Tool Call Detection**: `if response.tool_call:`
- **Status Update**: `self._update_status("executing")`

---

## 3. Tool Trimming
Composio and other external integrations have been removed. Gemini only sees screen control tools.

- **Tools in Config**: `SCREEN_TOOL_DECLARATIONS` in `aegis/voice.py`.
- **System Prompt**: Now focuses solely on screen control.

---

## 4. Security Gating (Authorization)
Every screen action must pass through the Aegis Secure Gateway.

- **Gateway Entry**: `aegis/gate.py` -> `gate_action`
- **Classification**: `classification = await classify_action(proposed_action, tool_hint=tool_name)` in `aegis/classifier.py`.
- **Risk Tiers**:
    - **RED (Biometric Required)**: Triggers Touch ID via `aegis/auth.py`.
    - **YELLOW (Verbal Required)**: Prompts the user for verbal confirmation.
    - **GREEN (Automatic)**: Proceeds directly to execution.

---

## 5. Execution (Action Delivery)
Once authorized, the action is routed specifically to the screen executor.

- **Routing Logic**: `if is_screen_tool(tool):` in `aegis/gate.py`.
- **Screen Execution**: `aegis/screen_executor.py` -> `execute_screen_action`.
    - Final Python calls (e.g., `pyautogui` via `aegis/screen/cursor.py`).

---

## 6. Feedback Loop (Closing the Turn)
After execution, results and screenshots are sent back to Gemini to confirm completion.

- **Screen Capture**: `shot = capture_screen()` in `voice.py`.
- **Sending Response**: `await session.send(input=types.LiveClientToolResponse(function_responses=...))`
- **Resuming Mic**: `self._update_status("listening")`
