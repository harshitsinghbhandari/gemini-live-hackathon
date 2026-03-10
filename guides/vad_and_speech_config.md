# VAD and Speech Configuration Guide
Created by Jules

## Current State
Aegis uses default Voice Activity Detection (VAD) settings and the "Aoede" voice. The current implementation in `aegis/voice.py` relies on basic SDK defaults, which may result in high latency for barge-ins or premature cut-offs in noisy environments. Audio sample rates are hardcoded to 16kHz (send) and 24kHz (receive).

## Target State
Optimize **AutomaticActivityDetection** and **SpeechConfig** for a more responsive and "human-like" interaction. This includes tuning sensitivity for speech detection and configuring prefix padding to prevent syllable clipping. The goal is to minimize the time between the user finishing their sentence and Aegis beginning its response.

## Migration Steps
1. **Configure VAD Sensitivity**:
   - In `aegis/voice.py`, update `LiveConnectConfig` to include `realtime_input_config`.
   - Set `start_of_speech_sensitivity` to `START_SENSITIVITY_HIGH` for faster trigger.
   - Set `end_of_speech_sensitivity` to `END_SENSITIVITY_HIGH` to detect the end of turns more aggressively.
2. **Tune Padding and Silence**:
   - Configure `prefix_padding_ms` (e.g., 200ms) to ensure the beginning of user speech isn't lost.
   - Set `silence_duration_ms` (e.g., 500ms) to balance responsiveness against accidental interruptions during pauses.
3. **Voice Selection**:
   - Update `PrebuiltVoiceConfig` to use specific high-fidelity voices like "Aoede" or "Fenrir" as available in the target model.
4. **Dynamic Sample Rates**:
   - Move sample rate configurations to `aegis/config.py` and ensure they match the requirements of the upgraded Native Audio models.

## Files Changed
- `aegis/voice.py`: Update `LiveConnectConfig` with detailed VAD and Speech settings.
- `aegis/config.py`: Centralize audio parameters and voice names.

## Gotchas
- **Sensitivity Trade-offs**: High sensitivity can lead to "false starts" in noisy environments. Implement a software-level gate or noise suppression if needed.
- **Voice Availability**: Not all voices are available in all regions or for all models. Verify voice support for the selected `GEMINI_LIVE_MODEL`.
- **Latency**: Large `silence_duration_ms` values will make the agent feel sluggish. Keep this under 1000ms for a "live" feel.
