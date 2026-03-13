"""
aegis/screen/type.py
Keyboard control: type text, press keys, hotkeys.
Tier classification:
  - Regular text typing = YELLOW
  - Passwords / sensitive fields = RED
  - Hotkeys (cmd+c, cmd+v etc.) = YELLOW
"""

import time
import pyautogui
import logging

logger = logging.getLogger(__name__)


# Mapping of common spoken key names to pyautogui key strings
KEY_ALIASES = {
    "enter": "enter",
    "return": "enter",
    "escape": "escape",
    "esc": "escape",
    "tab": "tab",
    "space": "space",
    "backspace": "backspace",
    "delete": "delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
    "page up": "pageup",
    "page down": "pagedown",
    "cmd": "command",
    "command": "command",
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "shift": "shift",
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4",
    "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8",
    "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
}


def type_text(text: str, interval: float = 0.04) -> dict:
    """
    Type a string of text character by character.
    YELLOW tier — requires voice confirmation.

    Args:
        text: The text to type
        interval: Seconds between keystrokes (makes it look natural)

    Returns:
        dict: {success, action, text}
    """
    try:
        import subprocess
        # Copy to clipboard via pbcopy (macOS native)
        process = subprocess.Popen(
            ["pbcopy"], stdin=subprocess.PIPE
        )
        process.communicate(text.encode("utf-8"))

        # Paste with Cmd+V
        logger.info(f"Typing text (clipboard method): {text[:20]}...")
        pyautogui.hotkey("command", "v")
        time.sleep(0.1)

        return {"success": True, "action": "type", "text": text}
    except Exception as e:
        logger.error(f"Failed to type text: {e}")
        return {"success": False, "error": str(e)}


def type_text_direct(text: str, interval: float = 0.04) -> dict:
    """
    Type text directly keystroke by keystroke (ASCII only, no unicode).
    Fallback if clipboard method has issues.
    YELLOW tier.
    """
    try:
        pyautogui.write(text, interval=interval)
        return {"success": True, "action": "type_direct", "text": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def press_key(key: str) -> dict:
    """
    Press a single key by name.
    Accepts spoken aliases like "enter", "escape", "tab".
    YELLOW tier.

    Args:
        key: Key name (see KEY_ALIASES for supported values)
    """
    try:
        normalized = key.lower().strip()
        pyautogui_key = KEY_ALIASES.get(normalized, normalized)
        pyautogui.press(pyautogui_key)
        return {"success": True, "action": "press_key", "key": pyautogui_key}
    except Exception as e:
        return {"success": False, "error": str(e)}


def hotkey(*keys: str) -> dict:
    """
    Press a key combination simultaneously.
    e.g. hotkey("command", "c") for Cmd+C
         hotkey("command", "shift", "4") for screenshot
    YELLOW tier.

    Args:
        keys: Key names in order (modifier first)
    """
    try:
        normalized = [KEY_ALIASES.get(k.lower().strip(), k.lower().strip()) for k in keys]
        logger.info(f"Pressing hotkey: {'+'.join(normalized)}")
        pyautogui.hotkey(*normalized)
        return {"success": True, "action": "hotkey", "keys": normalized}
    except Exception as e:
        logger.error(f"Failed to press hotkey: {e}")
        return {"success": False, "error": str(e)}


def type_sensitive(text: str) -> dict:
    """
    Type sensitive text (passwords, API keys, etc.).
    RED tier — requires biometric auth before calling.
    Uses clipboard method to avoid keylogger interception.
    """
    try:
        import subprocess
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(text.encode("utf-8"))
        pyautogui.hotkey("command", "v")
        time.sleep(0.1)

        # Clear clipboard immediately after pasting
        clear_process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        clear_process.communicate(b"")

        return {"success": True, "action": "type_sensitive", "text": "[REDACTED]"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def select_all() -> dict:
    """Cmd+A — select all text in focused field. YELLOW tier."""
    return hotkey("command", "a")


def copy() -> dict:
    """Cmd+C — copy selection. GREEN tier."""
    return hotkey("command", "c")


def paste() -> dict:
    """Cmd+V — paste clipboard. YELLOW tier."""
    return hotkey("command", "v")


def undo() -> dict:
    """Cmd+Z — undo last action. YELLOW tier."""
    return hotkey("command", "z")


if __name__ == "__main__":
    import time

    print("Testing type module...")
    print("Opening Spotlight in 2 seconds (Cmd+Space), then typing 'TextEdit'")
    print("Watch your screen!")
    time.sleep(2)

    # Open Spotlight
    result = hotkey("command", "space")
    print(f"Hotkey result: {result}")
    time.sleep(0.5)

    # Type in Spotlight
    result = type_text("TextEdit")
    print(f"Type result: {result}")
    time.sleep(0.5)

    # Press Escape to close Spotlight (don't actually open TextEdit)
    result = press_key("escape")
    print(f"Escape result: {result}")

    print("Done.")