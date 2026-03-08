# Aegis Reproducibility Guide

This guide ensures a seamless setup of Aegis from scratch. Follow these steps to get the agent running on your macOS environment.

## 📋 System Requirements

- **Operating System:** macOS (Intel or Apple Silicon)
- **Python:** 3.11, 3.12, or 3.13 (Python 3.14 compatibility is experimental)
- **Homebrew:** Required for system dependencies (`portaudio`)
- **Browser:** Google Chrome (recommended for app mode)

## 🚀 Quick Start (Automated)

The fastest way to install Aegis is using the automated install script:

```bash
curl -sSL https://aegis.projectalpha.in/install.sh | bash
```

### What this script does:
1. Verifies macOS and installs Homebrew if missing.
2. Installs `portaudio` via Homebrew.
3. Clones the Aegis repository.
4. Sets up a Python virtual environment and installs dependencies.
5. Starts the Helper Server and Agent in the background.
6. Opens the Aegis Dashboard.

## 🛠️ Manual Setup

If you prefer to set up manually, follow these steps:

### 1. Install System Dependencies
```bash
brew install portaudio
```

### 2. Clone and Prepare Environment
```bash
git clone https://github.com/projectalpha-dev/gemini-live-hackathon.git
cd gemini-live-hackathon
cp .env.example .env
```

### 3. Configure .env
Fill in your API keys in the `.env` file:
- `GOOGLE_API_KEY`: Get from [aistudio.google.com](https://aistudio.google.com)
- `COMPOSIO_API_KEY`: Get from [app.composio.dev](https://app.composio.dev)
- `USER_ID`: Your chosen username
- `DEVICE_ID`: A unique identifier (e.g., `my-macbook`)

### 4. Install Python Dependencies
On Apple Silicon (M1/M2/M3) Macs, you must point to the Homebrew PortAudio location:
```bash
export CPATH=$(brew --prefix portaudio)/include
export LIBRARY_PATH=$(brew --prefix portaudio)/lib
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Start the Services
```bash
# Start the helper server (required for the Mac PWA)
python3 -m aegis.helper_server &

# Start the agent
python3 main.py
```

## ❓ Troubleshooting

### `pyaudio` Installation Fails
If `pyaudio` fails to compile, ensure `portaudio` is installed and the `CPATH`/`LIBRARY_PATH` variables are set correctly as shown in Step 4 of the Manual Setup.

### Agent Won't Start
- Check `aegis.log` for error messages.
- Ensure your `.env` file is in the root directory and contains valid API keys.
- Verify that no other process is using port `8766` (Helper Server) or `8765` (WebSocket Server).

### Echo Issues
Always use headphones when interacting with Aegis to prevent the agent from hearing its own output.

## ⏱️ Estimated Setup Time
- **Automated:** < 3 minutes
- **Manual:** < 5 minutes
