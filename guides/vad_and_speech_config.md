# VAD and Speech Configuration

Aegis optimizes Voice Activity Detection (VAD) for a responsive, "human-like" interaction on macOS.

## Configuration

We use `AutomaticActivityDetection` in `aegis/voice.py` with high-sensitivity settings to support barge-in:

```python
automatic_activity_detection=types.AutomaticActivityDetection(
    disabled=False,
    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
    prefix_padding_ms=200,
    silence_duration_ms=500,
)
```

## Barge-in Handling

- **Latency**: High sensitivity ensures the agent stops talking immediately when the user interrupts.
- **State Cleanup**: When an interruption is detected (`response.server_content.interrupted`), the agent transitions back to `LISTENING` and flushes the audio output stream.
- **Visual Feedback**: The UI wave-forms reflect the interruption in real-time, signaling that the agent is now listening.

## Audio Quality

- **Sending**: 16kHz PCM (Mono).
- **Receiving**: 24kHz PCM (Mono).
- **Voice**: We use the "Aoede" voice profile for a professional, helpful persona.
