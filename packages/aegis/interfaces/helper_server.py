"""
Aegis Helper Server
A lightweight FastAPI server on http://localhost:8766 that lets the macOS PWA
start and stop the Python Aegis agent without touching the terminal.
"""
import subprocess
import time
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import logging
from configs.agent import config

app = FastAPI(title="Aegis Helper Server", version="1.0.0")

# Allow PWA (browser) to call this local server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent process state
agent_process: subprocess.Popen = None
start_time: float = None


@app.on_event("startup")
async def startup_event():
    """Register PIN with backend if configured."""
    if config.AEGIS_PIN and config.USER_ID:
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "user_id": config.USER_ID,
                    "pin": config.AEGIS_PIN
                }
                response = await client.post(
                    f"{config.BACKEND_URL}/auth/register-pin",
                    json=payload,
                    timeout=10.0
                )
                if response.status_code == 200:
                    print(f"✅ PIN registered successfully for user {config.USER_ID}")
                else:
                    print(f"⚠️ PIN registration failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error registering PIN during startup: {e}")

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/start")
async def start_agent():
    global agent_process, start_time
    if agent_process and agent_process.poll() is None:
        return {"started": False, "reason": "already running", "pid": agent_process.pid}

    # Start run_agent_main.py from repo root
    # File is at packages/aegis/interfaces/helper_server.py, so root is 4 levels up
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    agent_process = subprocess.Popen(
        [sys.executable, os.path.join(repo_root, "cmd/agent/run_agent_main.py")],
        cwd=repo_root,
        env=os.environ.copy()
    )
    start_time = time.time()
    return {"started": True, "pid": agent_process.pid}


@app.post("/stop")
async def stop_agent():
    global agent_process, start_time
    if agent_process and agent_process.poll() is None:
        agent_process.terminate()
        try:
            agent_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            agent_process.kill()
            agent_process.wait()
        agent_process = None
        start_time = None
        return {"stopped": True}
    return {"stopped": False, "reason": "not running"}


@app.get("/status")
async def status():
    global agent_process, start_time
    running = agent_process is not None and agent_process.poll() is None
    uptime = int(time.time() - start_time) if running and start_time else 0
    return {
        "running": running,
        "pid": agent_process.pid if running else None,
        "uptime_seconds": uptime,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8766, log_level="info")
