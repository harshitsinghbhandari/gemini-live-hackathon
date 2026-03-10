# Thinking Configuration Guide
Created by Jules

## Current State
Aegis currently provides direct responses from Gemini without an explicit reasoning or "thinking" phase visible to the system or the user. This can lead to "vibe-coding" or unpredictable tool call sequences when performing complex Mac automation tasks.

## Target State
Enable the native **ThinkingConfig** in the Gemini Live API. This allows the model to produce "thoughts" (chain-of-thought reasoning) before generating a final response or tool call. These thoughts help the model navigate complex UI layouts and plan multi-step Composio workflows with higher accuracy.

## Migration Steps
1. **Enable Thinking**:
   - In `aegis/voice.py`, update the `LiveConnectConfig` to include `thinking_config=ThinkingConfig(include_thoughts=True)`.
2. **Handle Thought Parts**:
   - Update the `_receive_and_play_loop` in `aegis/voice.py` to detect `part.thought` in the `model_turn`.
   - Log these thoughts internally for debugging and system audit.
3. **UI Propagation**:
   - Update `aegis/ws_server.py` to support a new `thought` event.
   - Broadcast the model's reasoning steps to the Aegis dashboard or Mac app UI so the user can see what the agent is "planning" (e.g., "I see the 'Send' button is at (500, 300), I will click it now.").
4. **Model Selection**:
   - Ensure the `GEMINI_LIVE_MODEL` is set to a version that supports `ThinkingConfig` (e.g., Gemini 3 models).

## Files Changed
- `aegis/voice.py`: Update config and receive loop to handle thought parts.
- `aegis/ws_server.py`: Add broadcast support for thoughts.
- `aegis/config.py`: Update to a thinking-capable model ID.

## Gotchas
- **Token Usage**: `ThinkingConfig` consumes additional tokens for the reasoning steps. Monitor usage to ensure it remains within budget.
- **Latency**: While thinking improves quality, it adds a small delay before the first audio byte or tool call. Tune the system prompt to keep reasoning concise.
- **Audio Exclusion**: Thoughts are textual and should never be processed by the `pyaudio` output stream.
