"""
Aegis Helper Server
A lightweight FastAPI server on http://localhost:8766 that lets the macOS PWA
start and stop the Python Aegis agent without touching the terminal.
"""

import os
import sys
import time
import asyncio
import logging
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from configs.agent import config

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("aegis-helper")

# ------------------------------------------------------------------
# Repo root resolution
# ------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_SCRIPT = REPO_ROOT / "cmd/agent/run_agent_main.py"

assert AGENT_SCRIPT.exists(), f"Agent script not found at: {AGENT_SCRIPT}"

# ------------------------------------------------------------------
# Start lock (prevents race condition on concurrent /start calls)
# ------------------------------------------------------------------

_start_lock = asyncio.Lock()

# ------------------------------------------------------------------
# Lifespan
# ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    # runtime state
    app.state.agent_process = None
    app.state.agent_log_file = None
    app.state.start_time = None
    app.state.verification_status = "idle"
    app.state.verification_task = None

    logger.info("Aegis helper server started")

    yield

    # graceful shutdown
    proc = app.state.agent_process
    if proc and proc.poll() is None:
        logger.info("Shutting down running agent")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    # close agent log file if open
    if app.state.agent_log_file:
        app.state.agent_log_file.close()

    logger.info("Aegis helper server stopped")

# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------

app = FastAPI(
    title="Aegis Helper Server",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

async def stop_agent(app: FastAPI):

    # cancel any in-flight verification task first
    task = app.state.verification_task
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    app.state.verification_task = None

    proc = app.state.agent_process
    if proc and proc.poll() is None:
        logger.warning("Stopping agent (pid=%s)", proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    # close and reset log file
    if app.state.agent_log_file:
        app.state.agent_log_file.close()
        app.state.agent_log_file = None

    app.state.agent_process = None
    app.state.start_time = None
    app.state.verification_status = "idle"

# ------------------------------------------------------------------
# Background PIN verification
# ------------------------------------------------------------------

async def verify_pin_background(app: FastAPI):

    app.state.verification_status = "verifying"

    retries = 5
    delay = 3

    # single client for all retry attempts
    async with httpx.AsyncClient() as client:

        for attempt in range(retries):

            try:
                payload = {
                    "user_id": config.USER_ID,
                    "pin": config.AEGIS_PIN,
                }

                r = await client.post(
                    f"{config.BACKEND_URL}/auth/verify-pin",
                    json=payload,
                    timeout=10,
                )

                if r.status_code == 200:
                    logger.info("PIN verification successful")
                    app.state.verification_status = "verified"
                    return

                if r.status_code in (401, 403):
                    logger.error("PIN rejected by server (status=%s)", r.status_code)
                    await stop_agent(app)
                    app.state.verification_status = "rejected"
                    return

                logger.warning(
                    "Unexpected verification response %s (attempt %s/%s)",
                    r.status_code, attempt + 1, retries,
                )

            except asyncio.CancelledError:
                logger.info("PIN verification task cancelled")
                raise  # let the cancellation propagate cleanly

            except Exception as e:
                logger.warning("Verification attempt %s/%s failed: %s", attempt + 1, retries, e)

            await asyncio.sleep(delay)

    logger.error("PIN verification failed after %s retries", retries)
    await stop_agent(app)
    app.state.verification_status = "failed"

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/start")
async def start_agent():

    async with _start_lock:

        if app.state.agent_process and app.state.agent_process.poll() is None:
            return {
                "started": False,
                "reason": "already running",
                "pid": app.state.agent_process.pid,
            }

        # cancel any stale verification task from a previous run
        old_task = app.state.verification_task
        if old_task and not old_task.done():
            old_task.cancel()
            try:
                await old_task
            except asyncio.CancelledError:
                pass
        app.state.verification_task = None

        # open a rotating-friendly log file for agent output
        log_path = REPO_ROOT / "logs" / "agent.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "a")

        logger.info("Starting agent (script=%s)", AGENT_SCRIPT)

        proc = subprocess.Popen(
            [sys.executable, str(AGENT_SCRIPT)],
            cwd=str(REPO_ROOT),
            env=os.environ.copy(),
            stdout=log_file,
            stderr=log_file,
        )

        app.state.agent_process = proc
        app.state.agent_log_file = log_file
        app.state.start_time = time.time()
        app.state.verification_status = "pending"

        app.state.verification_task = asyncio.create_task(
            verify_pin_background(app)
        )

        return {
            "started": True,
            "pid": proc.pid,
            "log": str(log_path),
            "verification": "running_in_background",
        }


@app.post("/stop")
async def stop():

    if not app.state.agent_process:
        return {"stopped": False, "reason": "not running"}

    await stop_agent(app)

    return {"stopped": True}


@app.get("/status")
async def status():

    proc = app.state.agent_process
    running = proc is not None and proc.poll() is None

    uptime = 0
    if running and app.state.start_time:
        uptime = int(time.time() - app.state.start_time)

    return {
        "running": running,
        "pid": proc.pid if running else None,
        "uptime_seconds": uptime,
        "verification": app.state.verification_status,
    }

@app.post("/combine")
async def combine_audio():
    """Stitches raw audio chunks into MP3 files."""
    data_dir = REPO_ROOT / "data"
    audio_dir = data_dir / "audio"
    sent_dir = audio_dir / "sent"
    received_dir = audio_dir / "received"

    def stitch_folder(folder, sample_rate, output_name):
        if not folder.exists(): return None
        files = sorted(list(folder.glob("*.raw")))
        if not files: return None
        
        # Simple Python join is most reliable for raw PCM chunks
        temp_raw = folder / "joined_temp.raw"
        try:
            with open(temp_raw, "wb") as outfile:
                for chunk_file in files:
                    with open(chunk_file, "rb") as infile:
                        outfile.write(infile.read())
            
            output_path = audio_dir / output_name
            cmd = [
                "ffmpeg", "-y",
                "-f", "s16le",
                "-ar", str(sample_rate),
                "-ac", "1",
                "-i", str(temp_raw),
                "-codec:a", "libmp3lame",
                "-qscale:a", "2",
                str(output_path)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            return output_name
        except Exception as e:
            logger.error(f"Failed to stitch {folder.name}: {e}")
            return None
        finally:
            if temp_raw.exists():
                temp_raw.unlink()

    sent_mp3 = stitch_folder(sent_dir, config.SEND_SAMPLE_RATE, f"sent_combined_{int(time.time())}.mp3")
    recv_mp3 = stitch_folder(received_dir, config.RECEIVE_SAMPLE_RATE, f"received_combined_{int(time.time())}.mp3")

    if not sent_mp3 and not recv_mp3:
         return {"success": False, "error": "No audio chunks found to combine."}

    return {
        "success": True,
        "sent": sent_mp3,
        "received": recv_mp3
    }

# ------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8766,
        log_level="info",
    )