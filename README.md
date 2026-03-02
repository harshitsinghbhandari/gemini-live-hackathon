# Guardian Agent

A trusted AI agent that controls your Mac using Gemini Live and Composio.

## Project Structure

- `voice_agent.py`: Main entry point. Run this to start the voice agent.
- `components/`: Core logic and integration modules.
  - `auth_gate.py`: Security layer with risk classification.
  - `auth.py`: Touch ID integration.
  - `risk_classifier.py`: Gemini-powered risk analysis.
  - `screen_capture.py`: Screen recording utility.
  - `composio_executor.py`: Tool execution via Composio.
  - `connect_gmail.py`: Helper to link your Gmail account.
- `tests/`: Test scripts for various components.
- `data/`: JSON data stores for logs and cached information.
- `composio/`: Package directory for Composio.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up your environment variables in `.env`.
3. Link Gmail:
   ```bash
   python -m components.connect_gmail
   ```
4. Run the agent:
   ```bash
   python voice_agent.py
   ```

## Running Tests

Run any test script from the root directory:
```bash
python -m tests.test_auth
```
