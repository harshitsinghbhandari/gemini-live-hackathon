"""
Aegis Launcher
Starts the helper server and opens the macOS PWA in browser app mode.
This is the single entry point for non-technical users.
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / 'packages'))
sys.path.insert(0, str(BASE_DIR))

import subprocess
import sys
import time
import webbrowser
import requests
import os

MAC_APP_URL = "https://aegismac.projectalpha.in"
HELPER_URL = "http://localhost:8766"


def start_helper_server():
    """Start helper server as background process"""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    process = subprocess.Popen(
        [sys.executable, "-m", "packages.aegis.interfaces.helper_server"],
        cwd=repo_root
    )
    # Wait for helper to be ready (up to 5 seconds)
    for _ in range(10):
        try:
            r = requests.get(f"{HELPER_URL}/health", timeout=1)
            if r.status_code == 200:
                print("✅ Helper server ready")
                return process
        except Exception:
            time.sleep(0.5)
    print("❌ Helper server failed to start")
    return None


def open_app():
    """Open PWA in Chrome app mode (feels like native app)"""
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for chrome in chrome_paths:
        if os.path.exists(chrome):
            subprocess.Popen([
                chrome,
                f"--app={MAC_APP_URL}",
                "--window-size=400,700",
                "--window-position=100,100",
            ])
            return
    # Fallback to default browser
    webbrowser.open(MAC_APP_URL)


if __name__ == "__main__":
    print("🛡️  Starting Aegis...")
    helper = start_helper_server()
    if helper:
        open_app()
        print("✅ Aegis launched")
        # Keep launcher alive while helper runs
        helper.wait()
