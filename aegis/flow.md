# Aegis Voice Flow Documentation

This document traces the exact execution path from the moment a user speaks to the completion of an action.

---

## 1. User Speaks (Audio Capture & Stream)
When the user speaks, the audio is captured via the microphone and streamed to the Gemini Live API.

- **Audio Capture Loop**: `aegis/voice.py` -> `AegisVoiceAgent._send_audio_loop` (Line 176)
- **Reading Chunk**: `data = await asyncio.to_thread(stream.read, config.CHUNK_SIZE, False)` (Line 194)
- **Broadcasting Waveform**: `ws_server.broadcast("waveform", value=round(peak, 3))` (Line 200)
- **Sending to Gemini**: `await session.send_realtime_input(audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={config.SEND_SAMPLE_RATE}"))` (Line 202)

---

## 2. Gemini Responds (Audio Playback & Tool Trigger)
Gemini processes the audio and responds with either audio (speech) or a tool call (action).

- **Reception Loop**: `aegis/voice.py` -> `AegisVoiceAgent._receive_and_play_loop` (Line 210)
- **Listening for Response**: `async for response in session.receive():` (Line 222)
- **Audio Playback**: `await asyncio.to_thread(output_stream.write, part.inline_data.data)` (Line 247)
- **Tool Call Detection**: `if response.tool_call:` (Line 249)
- **Status Update**: `self._update_status("executing")` (Line 251)

---

## 3. Tool Selection & Mapping
Gemini's tool calls are intercepted and mapped to Aegis-specific executors.

- **Iterating Tool Calls**: `for fn in response.tool_call.function_calls:` (Line 258)
- **Mapping ComputerUse (Native)**:
    - If `click_at`, `scroll`, `type_text_at`, etc., are received, they are mapped to `SCREEN_CLICK`, `SCREEN_SCROLL`, `SCREEN_TYPE`, etc. (Lines 286-314).
    - Coordinates are converted: `mapped_args["x"], mapped_args["y"] = self._denormalize(fn.args["x"], fn.args["y"])` (Line 288).
- **Direct Tool Call**: If it's a Composio or dynamic tool, it proceeds to the gate (Line 344).

---

## 4. Security Gating (Authorization)
Every action must pass through the Aegis Secure Gateway.

- **Gateway Entry**: `aegis/gate.py` -> `gate_action` (Line 105)
- **Classification**: `classification = await classify_action(proposed_action, tool_hint=tool_name)` (Line 122)
- **Risk Tiers**:
    - **RED (Biometric Required)**: `authed = await request_remote_auth(proposed_action, classification)` (Line 162). This polls the backend or triggers Touch ID.
    - **YELLOW (Verbal Required)**: Returns `result["needs_confirmation"] = True` (Line 178) to `voice.py`, which prompts the user.
    - **GREEN (Automatic)**: Proceeds directly to execution.

---

## 5. Execution (Action Delivery)
Once authorized, the action is routed to the appropriate executor.

- **Routing Logic**: `if is_screen_tool(tool):` (Line 199) or `else: await execute_composio_tool(...)` (Line 205).
- **Screen Execution**: `aegis/screen_executor.py` -> `execute_screen_action` (Line 314).
    - Dispatches to: `result = await _dispatch(tool_name, args)` (Line 325).
    - Final Python calls (e.g., `pyautogui` via `aegis/screen/cursor.py`): `return click(args["x"], args["y"])` (Line 258).
- **Composio Execution**: `aegis/executor.py` -> `execute_composio_tool` (Line 210).
    - Final API call: `execute_result = await asyncio.to_thread(context.composio.tools.execute, slug=tool_name, ...)` (Line 223).

---

## 6. Feedback Loop (Closing the Turn)
After execution, results and screenshots are sent back to Gemini to confirm completion.

- **Screen Capture**: `shot = capture_screen()` (Line 366 in `voice.py`).
- **Sending Response**: `await session.send(input=types.LiveClientToolResponse(function_responses=...))` (Line 383).
- **Resuming Mic**: `self._update_status("listening")` (Line 393).
