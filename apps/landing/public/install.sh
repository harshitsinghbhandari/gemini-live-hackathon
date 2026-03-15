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

# Directory handling for the repo
if [ ! -d "gemini-live-hackathon" ]; then
    if [ "${PWD##*/}" == "gemini-live-hackathon" ]; then
        echo "✅ Already in the Aegis repository directory."
    else
        echo "🐙 Cloning Aegis repository..."
        git clone https://github.com/harshitsinghbhandari/gemini-live-hackathon.git
        cd gemini-live-hackathon
    fi
else
    cd gemini-live-hackathon
    git pull
fi

if [ ! -f "../.env" ] && [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Please create a .env file with your GOOGLE_API_KEY and other required variables."
    exit 1
fi

# Move .env if it's in parent dir
if [ -f "../.env" ]; then
    mv ../.env ./.env
fi

echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "🚀 Starting Aegis Agent..."
# Start the agent and helper server
# Kill existing agent/helper if running
pkill -f "python -m aegis.main" || true
pkill -f "python -m aegis.helper_server" || true

export PYTHONPATH=$PYTHONPATH:$(pwd)/packages
nohup python -m aegis.interfaces.helper_server > helper.log 2>&1 &
nohup python cmd/agent/run_agent_main.py > aegis.log 2>&1 &
echo "✅ Agent and Helper Server are running in the background."

echo "🌐 Opening Aegis Dashboard..."
# Launch Chrome as an app if available
if [ -d "/Applications/Google Chrome.app" ]; then
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --app="https://aegis.projectalpha.in" &
else
    open "https://aegis.projectalpha.in"
fi

echo "🎉 Installation complete. Your local agent is now active and protecting you."
