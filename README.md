# 🛡️ Guardian

Guardian is a voice-controlled, biometric-secured AI agent for macOS that uses Gemini Live to hear you and see your screen in real time. It intelligently classifies every proposed action into risk tiers, requiring Touch ID for sensitive operations before executing them via Composio. Guardian ensures that your AI assistant is both powerful and trustworthy by keeping you in control of every irreversible action.

## 🏗️ Architecture

```text
Voice/Screen → Gemini Live → Risk Classifier → Auth Gate → Composio → Speaks Result
                                  │               │
                                  │               ├─ 🟢 GREEN: Execute silently
                                  │               ├─ 🟡 YELLOW: Verbal confirmation
                                  └───────────────┴─ 🔴 RED: Touch ID Authentication
```

## 🛠️ Tech Stack

- **Gemini Live API**: Real-time, low-latency voice and tool-use interaction.
- **Gemini Vision**: Periodic screen captures for context-aware assistance.
- **Composio Tool Router**: Intelligent discovery and execution of 100+ tools.
- **macOS LocalAuthentication**: Secure biometric verification via Touch ID.
- **PyAudio**: Direct hardware access for mic input and speaker output.
- **Google GenAI SDK**: The official Python client for Gemini models.
- **Python asyncio**: Manages concurrent audio, vision, and execution streams.

## 📂 Project Structure

- `main.py`: Entry point that initializes the logging and starts the agent.
- `guardian/config.py`: Centralized API keys, model names, and audio settings.
- `guardian/context.py`: Dataclass for session state and shared resources.
- `guardian/voice.py`: Core Gemini Live websocket logic and audio processing.
- `guardian/screen.py`: Handles periodic high-quality screen captures.
- `guardian/classifier.py`: Uses Gemini to map intent to tools and security tiers.
- `guardian/gate.py`: The "Security Brain" that enforces tiers and logs actions.
- `guardian/auth.py`: macOS-specific Touch ID integration.
- `guardian/executor.py`: Routes and executes actions through the Composio ecosystem.

## 🚀 Setup Instructions

### Prerequisites
- macOS device with **Touch ID**
- Python 3.11 or higher
- [Google AI Studio API Key](https://aistudio.google.com/)
- [Composio API Key](https://app.composio.dev/)

### Installation
1. Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_google_api_key
   COMPOSIO_API_KEY=your_composio_api_key
   USER_ID=your_email_or_unique_id
   ```

3. Connect your Google accounts via Composio:
   ```bash
   composio add gmail
   composio add googlecalendar
   ```

### Running Guardian
```bash
python main.py
```
*Note: Use headphones to prevent the agent from hearing its own voice output.*

## 🛡️ How It Works (Security Tiers)

Every action Guardian takes is filtered through a three-tier security gate:

- 🟢 **GREEN** (Read-only): Checking your calendar or reading emails. Guardian executes these silently and reports the findings.
- 🟡 **YELLOW** (Sensitive): Replying to an existing email thread. Guardian will verbally ask "Should I proceed?" and wait for your confirmation.
- 🔴 **RED** (Irreversible): Deleting data or creating new drafts for external contacts. Guardian triggers a system-level Touch ID prompt; execution only proceeds upon successful biometric scan.

## 🎙️ Supported Actions

Guardian currently supports deep integration with Gmail and Google Calendar:

- **Gmail**:
  - *"Do I have any new emails about the project?"*
  - *"Draft a reply to Sarah saying I'll be there."*
  - *"Reply to the latest thread from my boss."*
- **Google Calendar**:
  - *"What's on my schedule for tomorrow morning?"*
  - *"Book a meeting with Dave for Friday at 2 PM."*

## 📝 Audit Trail
Every action attempted by the agent is logged to `guardian_audit.jsonl`. Each entry includes a timestamp, the proposed action, security tier, auth status, success/failure, and the total execution time in milliseconds.

## 🏆 Hackathon Context
Built for the **Gemini Live Agent Challenge**. Guardian demonstrates that AI agents can be both powerful and trustworthy — biometric-secured, context-aware, and fully transparent.
