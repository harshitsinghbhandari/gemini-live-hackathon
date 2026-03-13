#!/bin/bash
set -e

echo "🛡️ Installing Aegis Agent..."

# Ensure we're on macOS
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "❌ Error: Aegis currently requires macOS."
    exit 1
fi

# Ensure Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "🍺 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

echo "📦 Installing required macOS packages (portaudio)..."
brew install portaudio

# Export PortAudio paths for M1/M2/M3 Macs to ensure pyaudio installs correctly
if [[ "$(uname -m)" == "arm64" ]]; then
    export CPATH=$(brew --prefix portaudio)/include
    export LIBRARY_PATH=$(brew --prefix portaudio)/lib
fi

# Directory handling for the repo
if [ ! -d "gemini-live-hackathon" ]; then
    if [ "${PWD##*/}" == "gemini-live-hackathon" ]; then
        echo "✅ Already in the Aegis repository directory."
    else
        echo "🐙 Cloning Aegis repository..."
        git clone https://github.com/projectalpha-dev/gemini-live-hackathon.git
        cd gemini-live-hackathon
    fi
else
    cd gemini-live-hackathon
    git pull
fi

if [ ! -f "../.env" ] && [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Please download it from the Dashboard Setup Page and place it in this directory or the parent directory."
    exit 1
fi

# Move .env if it's in parent dir
if [ -f "../.env" ]; then
    mv ../.env ./.env
fi

echo "🐍 Setting up Python virtual environment..."
# Check if python3 is available and version is 3.11+
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed. Please install Python 3.11+."
    exit 1
fi

PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "❌ Error: Aegis requires Python 3.11+, but you have $PYTHON_MAJOR.$PYTHON_MINOR."
    exit 1
fi

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "🚀 Starting Aegis Agent..."
# Start the agent and helper server
# Kill existing agent/helper if running
pkill -f "python3 cmd/agent/run_agent_main.py" || true
pkill -f "python3 cmd/agent/run_agent.py" || true

nohup python3 cmd/agent/run_agent.py > helper.log 2>&1 &
nohup python3 cmd/agent/run_agent_main.py > aegis.log 2>&1 &
echo "✅ Agent and Helper Server are running in the background."

echo "🌐 Opening Aegis Dashboard..."
# Launch Chrome as an app if available
if [ -d "/Applications/Google Chrome.app" ]; then
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --app="https://aegis.projectalpha.in" &
else
    open "https://aegis.projectalpha.in"
fi

echo "🎉 Installation complete. Your local agent is now active and protecting you."
