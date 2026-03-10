# Computer Use Integration Guide
Created by Jules

## Current State
Aegis uses manual `pyautogui` wrappers in `aegis/screen/` for screen control. Coordinate scaling is handled by a custom `_denormalize` function in `aegis/voice.py` to map from model outputs to a hardcoded 1470x956 resolution. Screenshots are captured and sent manually after every tool execution to update the model's visual context.

## Target State
Transition to the native **ComputerUse** tool provided by the SDK. This tool standardizes coordinate handling (normalized to 0-1000) and allows the model to interact with the OS more natively. Aegis will act as the "Client-Side Action Handler," executing native SDK actions (`click_at`, `type_text_at`, etc.) using its existing hardware-level executors.

## Migration Steps
1. **Declare Tool**: Add `Tool(computer_use=ComputerUse(environment=Environment.ENVIRONMENT_BROWSER))` to the `LiveConnectConfig` in `aegis/voice.py`.
2. **Implement Action Mapping**:
   - Update the `_receive_and_play_loop` in `aegis/voice.py` to parse `response.tool_call.computer_use`.
   - Map native actions like `navigate` to `SCREEN_TYPE` or a new browser handler.
   - Map `click_at`, `double_click_at`, etc., to the existing functions in `aegis/screen/cursor.py`.
3. **Standardize Coordinates**:
   - Update `_denormalize` to use the model's 0-1000 scale and dynamic screen dimensions instead of hardcoded values.
4. **Auth Gating**:
   - Wrap every native action in a call to `gate_action` to maintain the tiered security model (e.g., `click_at` should still be YELLOW).
5. **Context Updates**:
   - Instead of manual screenshots in the agent loop, provide the fresh screenshot in the `function_response` parts for the native tool.

## Files Changed
- `aegis/voice.py`: Update tool declarations and native tool call handler.
- `aegis/screen_executor.py`: Potentially retire redundant manual tool definitions in favor of native SDK types.

## Gotchas
- **Coordinate Range**: The model expects 0-1000 for both X and Y. Ensure the `denormalize` logic correctly maps to the user's primary monitor resolution.
- **Environment**: `Environment.ENVIRONMENT_BROWSER` is currently the supported environment type for most computer use models.
- **Safety**: Native computer use allows for faster execution. Ensure the `YELLOW` confirmation logic in `gate.py` is non-blocking to the WebSocket heartbeats to prevent timeouts during user confirmation.
