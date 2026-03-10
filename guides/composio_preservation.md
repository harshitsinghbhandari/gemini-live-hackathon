# Composio Preservation Guide
Created by Jules

## Current State
Aegis integrates Composio for executing actions in third-party apps (Gmail, Calendar, etc.). It currently uses a manual "Tool Router" pattern (`aegis/executor.py`) to search for tools and a custom argument-filling step using Gemini. Most importantly, every Composio action is passed through `gate_action` in `aegis/gate.py` for GREEN/YELLOW/RED classification and biometric/verbal auth.

## Target State
Transition to the SDK's native tool-calling protocol for Composio while preserving the Aegis Security Gateway. Instead of a manual search-and-execute loop, Composio tools will be declared directly to Gemini. When Gemini calls a tool, the execution will be intercepted, sent to `gate.py` for authorization, and only then executed via the Composio client.

## Migration Steps
1. **Native Declarations**: Use the Composio SDK to export tool schemas in a format compatible with `google.genai.types.Tool`.
2. **Intercept Tool Calls**:
   - In `aegis/voice.py`, when `response.tool_call.function_calls` contains a Composio-prefixed tool (e.g., `GMAIL_...`):
   - Extract the tool name and arguments.
   - Pass them to `gate_action(simulated_action, context, tool_name=name, tool_args=args)`.
3. **Handle Blocking Auth**:
   - For RED actions, ensure the `request_remote_auth` poll is non-blocking to the main event loop.
   - If auth fails or is denied, return a `function_response` to Gemini stating that the action was blocked for security.
4. **Preserve User ID Context**:
   - Ensure the `config.COMPOSIO_USER_ID` is correctly passed through the native tool executor to maintain multi-user isolation.

## Files Changed
- `aegis/executor.py`: Update or retire manual `search_and_execute` logic.
- `aegis/voice.py`: Implement the native tool call interception and security wrapper.
- `aegis/gate.py`: Ensure `classify_action` can handle direct tool names as hints (already partially implemented).

## Gotchas
- **Parallel Execution**: Native tool calls can be parallel. The Aegis Gateway must handle this by either queuing auth requests or prompting the user for a batch confirmation.
- **Biometric Timeouts**: Biometric auth (Touch ID) has a 30-second timeout. If the user doesn't respond, the session must handle the tool failure gracefully without crashing the WebSocket.
