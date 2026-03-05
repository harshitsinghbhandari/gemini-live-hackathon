# Aegis Agent - Project Context

This file contains comprehensive context about the Aegis Agent repository to help any AI agent understand the architecture, core modules, and how everything interacts.

## 1. Project Overview & Architecture

**Aegis** is an AI agent that controls a Mac computer using the Gemini Live API and Composio. It uses a multi-modal approach (Voice + Screen) to interpret user intent, classifies the security risk of actions, and executes them (often via Composio). High-risk actions (categorized as "RED") trigger a native ToucID/FaceID prompt.

**Key Technical Stack**:
- **Python**: Main application language.
- **Gemini Live API**: Handles real-time audio I/O and visual context (screenshots every 3 seconds) and calls tools.
- **Composio**: Platform used to execute actual API actions (e.g., fetching emails, drafting emails).
- **macOS LocalAuthentication framework**: Invoked via PyObjC to natively request Touch ID.
- **PyAudio**: For listening to system mic and playing back Gemini's audio responses.

## 2. Directory Structure

- `voice_agent.py`: The main entrypoint. Starts listening to the mic, takes screenshots and sends them to Gemini. Receives audio and function calls.
- `components/`: Core functional capabilities.
  - `auth_gate.py`: Classifies an action's risk. If RED, triggers TouchID. If GREEN, executes via Composio directly.
  - `auth.py`: Simple wrapper around macOS LocalAuthentication to ask for Touch ID.
  - `risk_classifier.py`: The raw logic to ask Gemini to classify an action as RED/YELLOW/GREEN.
  - `screen_capture.py`: Takes screenshots using PIL's `ImageGrab` and resizes them for Gemini.
  - `composio_executor.py`: Wrapper for Composio's Python SDK to run tools or connect an app.
  - `connect_gmail.py`: Helper script to trigger OAuth flow for Gmail on Composio.
- `tests/`: Various tests (`test_auth.py`, `test_classifier.py`, `test_composio.py`, `test_full_pipeline.py`, `test_gate.py`).
- `data/`: Temporary JSON dumps (`dump.json`, `emails.json`).
- `docs/`: Stores Comprehensive guides, specifically for Composio (`COMPOSIO_COMPREHENSIVE_GUIDE.md`, `COMPOSIO_GUIDE.md`).
- `generative-ai/`: Additional resources/code (186 children, primarily non-core repository items).
- `.env`: Holds API keys `GOOGLE_API_KEY` and `COMPOSIO_API_KEY`.

---

## 3. Core Files Reference

### `voice_agent.py`
This is the main orchestration script. It initializes `genai.Client`, connects to gemini's live api (`live.connect`), sets up system instructions, and exposes one tool to Gemini: `execute_action(action: str)`.
It runs 2 concurrent tasks:
1. `send_audio`: Reads mic continuously.
2. `receive_and_play`: Receives audio from Gemini (played via speaker) and handles the `execute_action` tool call by passing arguments to `gate_action()` from `components.auth_gate`.

### `components/auth_gate.py`
Handles security routing.
1. Receives an action string.
2. Captures a screenshot.
3. Sends both to Gemini via `classify_action()` to determine tier.
4. Rules:
   - RED: Prompt for Touch ID via `request_touch_id()`. Actions include: financial, external sending, deletion.
   - YELLOW: Requires confirmation.
   - GREEN: Executed silently.
5. Runs the suggested Composio `tool` using the suggested `arguments`.

### `components/auth.py`
Uses `objc` and `LocalAuthentication` frameworks.
Exposes `request_touch_id(reason: str) -> bool`. This runs asynchronously, waiting up to 30s.

### `components/risk_classifier.py`
Standalone file containing prompt instructions to assess risk:
- Returns JSON with `{"tier": "RED"|"YELLOW"|"GREEN", "reason": "...", "upgraded": bool, "speak": "..."}`.
- *Note: `auth_gate.py` functionally implements this itself.* 

### `components/screen_capture.py`
Uses `ImageGrab.grab().resize((1280, 720))` and saves to JPEG format in a BytesIO buffer. Returns the `base64` encoded string.

### `components/composio_executor.py`
Connects to Composio using `COMPOSIO_API_KEY`. Hardcoded `USER_ID = "harshitbhandari0318"`.
Functions include `execute_action(tool_name, arguments)` (which invokes `composio.tools.execute`), `connect_app(toolkit_slug)`, and `is_connected(toolkit_slug)`. It uses `dangerously_skip_version_check=True` to execute.

---

## 4. How to Extend
- **Adding new capabilities**: Define a new Composio tool or a local Python script function. Update the prompt in `auth_gate.py` to make the classifier aware of the new tools and acceptable tool names.
- **Troubleshooting Audio**: PyAudio settings (`SEND_SAMPLE_RATE = 16000`, `RECEIVE_SAMPLE_RATE = 24000`, `CHUNK_SIZE = 1024`). `is_executing_tool` global boolean is used to pause audio input during execution to prevent recursive loops or hearing its own execution output.
- **Handling Data Limits**: In `voice_agent.py`, text output length back to Gemini is truncated to 2000 chars to avoid WebSocket frame size limit errors (`1008 policy violation`).
