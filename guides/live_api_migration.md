# Live API Migration Guide
Created by Jules

## Current State
Aegis currently uses the **Gemini 2.0 Flash Native Audio** preview model (`gemini-2.0-flash-native-audio-preview-12-2025`). The bidirectional streaming implementation in `aegis/voice.py` uses a custom `pyaudio` loop but does not fully leverage the newer SDK signals for interruptions and turn boundaries.

## Target State
Upgrade to **Gemini 2.5 Flash Native Audio** (`gemini-2.5-flash-native-audio-latest`) or **Gemini 3 Flash** (`gemini-3-flash-preview`). The target implementation should utilize the standardized `google-genai` SDK patterns for low-latency bidirectional voice, ensuring natural barge-in handling and accurate turn completion signals.

## Migration Steps
1. **Update Model Constants**:
   - Change `GEMINI_LIVE_MODEL` in `aegis/config.py` to the target model ID.
2. **Refine Interruption Logic**:
   - In `aegis/voice.py`, update the `_receive_and_play_loop` to check the `response.server_content.interrupted` flag.
   - Immediately call `output_stream.stop()` and clear any pending audio buffers when `interrupted` is true to ensure natural barge-in behavior.
3. **Handle Turn Completion**:
   - Use the `turn_complete` signal from the server to accurately reset the `is_speaking` state and update the UI via `ws_server.broadcast`.
4. **Modality Filtering**:
   - Ensure the receive loop handles `model_turn` parts that contain thoughts or text (for thinking models) without attempting to play them as audio.

## Files Changed
- `aegis/config.py`: Update model ID and potentially regional endpoint settings.
- `aegis/voice.py`: Refactor `_receive_and_play_loop` for interruption and turn handling.

## Gotchas
- **Session Limits**: Gemini Live sessions have duration limits (typically 15 minutes for audio-only). Implement reconnection logic using `session_resumption` if available in the SDK.
- **Regional Endpoints**: Native audio capabilities are often tied to specific regional endpoints (e.g., `us-central1`). Ensure the client initialization matches the availability of the model.
- **Sample Rates**: Ensure the `RECEIVE_SAMPLE_RATE` remains consistent with the model's output (usually 24000Hz PCM).
