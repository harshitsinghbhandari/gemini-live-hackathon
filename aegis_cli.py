#!/usr/bin/env python3
"""
Aegis CLI — The trust layer for AI agents.
Commands: init, start, status, stop, combine
"""

import os
import sys
import json
import time
import random
import signal
import subprocess
import urllib.request
import urllib.error
import argparse
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

AEGIS_DIR       = Path.home() / ".aegis"
ENV_FILE        = AEGIS_DIR / ".env"
PID_FILE        = AEGIS_DIR / "helper.pid"
# Using same default as backend/config
DEFAULT_BACKEND = "https://apiaegis.projectalpha.in"
MAC_APP_URL     = "https://aegismac.projectalpha.in"
MOBILE_APP_URL  = "https://aegismobile.projectalpha.in"
DASHBOARD_URL   = "https://aegisdashboard.projectalpha.in"

# ── ANSI colours ─────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    DIM    = "\033[2m"

def banner():
    print(f"""
{C.CYAN}{C.BOLD}
   ▄████████    ▄████████    ▄██████▄   ▄█     ▄████████ 
  ███    ███   ███    ███   ███    ███ ███    ███    ███ 
  ███    ███   ███    █▀    ███    █▀  ███▌   ███    █▀  
  ███    ███  ▄███▄▄▄       ███        ███▌   ███        
▀███████████ ▀▀███▀▀▀       ███        ███▌ ▀███████████ 
  ███    ███   ███    █▄    ███    █▄  ███           ███ 
  ███    ███   ███    ███   ███    ███ ███     ▄█    ███ 
  ███    █▀    ██████████    ▀██████▀  █▀    ▄████████▀  
{C.RESET}
{C.DIM}  The trust layer for AI agents.{C.RESET}
""")

def ok(msg):    print(f"  {C.GREEN}✓{C.RESET}  {msg}")
def info(msg):  print(f"  {C.CYAN}→{C.RESET}  {msg}")
def warn(msg):  print(f"  {C.YELLOW}⚠{C.RESET}  {msg}")
def err(msg):   print(f"  {C.RED}✗{C.RESET}  {msg}")
def bold(msg):  print(f"\n{C.BOLD}{msg}{C.RESET}")

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_backend_url():
    """Get the backend URL from environment or .env file."""
    env = load_env()
    return os.environ.get("BACKEND_URL") or env.get("BACKEND_URL") or DEFAULT_BACKEND

def api_request(path, method="GET", payload=None):
    """Network helper using urllib."""
    url = f"{get_backend_url()}{path}"
    data = json.dumps(payload).encode() if payload else None
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Aegis-CLI/1.0"
    }
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
            return None, (e.code, body)
        except:
            return None, (e.code, str(e))
    except Exception as e:
        return None, str(e)

def prompt(label, secret=False, default=None):
    suffix = f" [{default}]" if default else ""
    display = f"  {C.BOLD}{label}{suffix}:{C.RESET} "
    if secret:
        import getpass
        val = getpass.getpass(display)
    else:
        val = input(display).strip()
    return val if val else default

def confirm(question, default=True):
    hint = "Y/n" if default else "y/N"
    raw = input(f"  {C.BOLD}{question}{C.RESET} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")

def load_env():
    if not ENV_FILE.exists():
        return {}
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env

def write_env(values: dict):
    AEGIS_DIR.mkdir(parents=True, exist_ok=True)
    # Persist existing ones if not provided
    current = load_env()
    current.update(values)
    lines = [f"{k}={v}" for k, v in current.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n")
    ENV_FILE.chmod(0o600)

def check_username(username: str):
    data, error = api_request(f"/auth/exists/{username}")
    if error:
        return True, f"Could not verify (backend unreachable): {error}"
    return not data.get("exists", False), None

def register_user(username: str, pin: str):
    payload = {"user_id": username, "pin": pin}
    return api_request("/auth/register-pin", method="POST", payload=payload)

def check_dependency(cmd):
    try:
        subprocess.run([cmd, "-version" if cmd == "ffmpeg" else "--version"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_init(args):
    banner()
    bold("Setting up Aegis on your machine.")

    if ENV_FILE.exists():
        warn("An existing Aegis installation was found.")
        if not confirm("Reset and reconfigure?", default=False):
            info("Config kept. Run 'aegis start' to launch.")
            return
    
    # Check dependencies
    if not check_dependency("ffmpeg"):
        warn("ffmpeg not found. Audio stitching (/combine) will not work.")
    
    # Step 1: Username
    bold("Step 1 — Choose your Aegis username")
    while True:
        username = prompt("Username")
        if not username: continue
        info("Checking availability…")
        available, err_msg = check_username(username)
        if err_msg:
            err(f"Verification failed: {err_msg}")
            err("Operation aborted. Please check your connection or try again later.")
            sys.exit(1)
        if available:
            ok(f"'{username}' is available.")
            break
        err(f"'{username}' is already taken. Try another.")

    # Step 2: PIN
    bold("Step 2 — Set a PIN")
    while True:
        pin = prompt("PIN (exactly 4 digits)", secret=True)
        if not pin or not pin.isdigit() or len(pin) != 4:
            err("PIN must be exactly 4 digits.")
            continue
        pin_confirm = prompt("Confirm PIN", secret=True)
        if pin != pin_confirm:
            err("PINs do not match.")
            continue
        break
    
    # Step 3: API Keys
    bold("Step 3 — API Keys")
    info("Gemini: aistudio.google.com")
    g_key = prompt("GOOGLE_API_KEY", secret=True)
    
    # Step 4: Backend Registration
    bold("Step 4 — Registering with backend…")
    _, reg_err = register_user(username, pin)
    if reg_err:
        warn(f"Backend registration failed: {reg_err}")
    else:
        ok("Registered.")

    write_env({
        "USER_ID": username,
        "DEVICE_ID": f"{username}-mac",
        "GOOGLE_API_KEY": g_key or "",
        "BACKEND_URL": get_backend_url(),
        "AEGIS_PIN": pin,
    })
    ok(f"Saved to {ENV_FILE}")

def cmd_start(args):
    if not ENV_FILE.exists():
        err("Run 'aegis init' first.")
        return

    env = load_env()
    for k, v in env.items():
        os.environ.setdefault(k, v)

    script_dir = Path(__file__).parent
    helper_paths = [
        script_dir / "packages" / "aegis" / "interfaces" / "helper_server.py",
        script_dir / "aegis" / "helper_server.py",
        script_dir / "helper_server.py",
    ]
    helper = next((p for p in helper_paths if p.exists()), None)
    if not helper:
        err("helper_server.py not found.")
        return

    bold("Starting Aegis…")
    c_env = os.environ.copy()
    c_env["PYTHONPATH"] = str(script_dir) + (f":{c_env['PYTHONPATH']}" if "PYTHONPATH" in c_env else "")
    
    proc = subprocess.Popen(
        [sys.executable, str(helper)],
        env=c_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    PID_FILE.write_text(str(proc.pid))
    ok(f"Helper running (PID {proc.pid})")
    
    time.sleep(1)
    if not args.no_open:
        try: subprocess.Popen(["open", MAC_APP_URL])
        except: pass

    info(f"Mac     : {MAC_APP_URL}")
    info(f"Mobile  : {MOBILE_APP_URL}")
    info(f"Audit   : {DASHBOARD_URL}")
    
    def _stop(sig, frame):
        print(f"\n  Stopping…")
        proc.terminate()
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, _stop)
    proc.wait()

def cmd_stop(args):
    if not PID_FILE.exists():
        warn("Not running.")
        return
    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        ok(f"Stopped (PID {pid})")
    except:
        warn("Process not found.")
        PID_FILE.unlink(missing_ok=True)

def cmd_status(args):
    env = load_env()
    running = False
    if PID_FILE.exists():
        try:
            os.kill(int(PID_FILE.read_text().strip()), 0)
            running = True
        except: pass

    bold("Aegis Status")
    print(f"  User      : {C.CYAN}{env.get('USER_ID', '—')}{C.RESET}")
    print(f"  Backend   : {C.CYAN}{env.get('BACKEND_URL', DEFAULT_BACKEND)}{C.RESET}")
    st = f"{C.GREEN}running{C.RESET}" if running else f"{C.DIM}stopped{C.RESET}"
    print(f"  Agent     : {st}")
    
    # Ping local helper
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/status", timeout=1) as r:
            data = json.loads(r.read().decode())
            if data.get("running"):
                ok("Agent process is active inside helper.")
            else:
                warn("Helper is running but agent is idle.")
    except:
        if running: warn("Helper PID exists but HTTP interface is unreachable.")

def cmd_combine(args):
    """Trigger the audio stitching on the helper server."""
    try:
        req = urllib.request.Request("http://127.0.0.1:8766/combine", method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            if data.get("success"):
                ok("Audio combined successfully.")
                if data.get("sent"): info(f"Sent: {data['sent']}")
                if data.get("received"): info(f"Received: {data['received']}")
            else:
                err(f"Failed: {data.get('error')}")
    except Exception as e:
        err(f"Could not reach helper server: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Aegis CLI — The trust layer for AI agents.")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("init", help="Initialise Aegis on this machine")
    
    start_parser = subparsers.add_parser("start", help="Start the agent and companion app")
    start_parser.add_argument("--no-open", action="store_true", help="Don't open the Mac app browser automatically")
    
    subparsers.add_parser("stop", help="Stop the running agent")
    subparsers.add_parser("status", help="Show current status")
    subparsers.add_parser("combine", help="Trigger audio stitching of recent sessions")

    if len(sys.argv) == 1:
        banner()
        parser.print_help()
        return

    args = parser.parse_args()
    cmds = {
        "init": cmd_init,
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "combine": cmd_combine,
    }
    
    if args.command in cmds:
        try: cmds[args.command](args)
        except KeyboardInterrupt: print("\nInterrupted.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()