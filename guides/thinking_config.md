# ThinkingConfig & Agentic Transparency

Aegis leverages Gemini's reasoning capabilities to provide a transparent user experience. By enabling `ThinkingConfig`, we separate the agent's internal "thought process" from its external "spoken response."

## Implementation

In `aegis/voice.py`, the agent is configured with:
```python
thinking_config=ThinkingConfig(include_thoughts=True)
```

## How Thoughts are Handled

1.  **Capture**: In `_receive_and_play_loop`, we listen for parts of the response where `getattr(part, "thought", False)` is true.
2.  **Broadcast**: These thoughts are immediately broadcast via WebSockets: `ws_server.broadcast("thought", value=part.text)`.
3.  **Visualization**: The Mac PWA and Dashboard display these thoughts in a dedicated "Thinking" area, allowing the user to see the agent's plan before it executes.

## Benefits for Trust

This transparency is core to the Aegis "Trust Layer":
- **Expectation Management**: Users see what the agent intends to do.
- **Error Detection**: If the agent's reasoning is flawed, the user can barge-in and correct it before an action is taken.
- **Security Audit**: Thoughts are included in the `aegis_audit.jsonl` log, providing a complete record of why an action was proposed.
