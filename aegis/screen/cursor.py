"""
aegis/screen/cursor.py
Mouse control: move, click, double-click, right-click, scroll.
All actions are intentionally explicit — no magic, no retries.
"""

import time
import pyautogui

# Safety: pyautogui will raise an exception if mouse hits screen corner
# This is a good failsafe — keeps the user in control
pyautogui.FAILSAFE = True

# Small delay between actions — makes automation look natural and reduces errors
pyautogui.PAUSE = 0.05


def move(x: int, y: int, duration: float = 0.0) -> dict:
    """
    Move cursor to (x, y) smoothly.
    
    Args:
        x, y: Target coordinates
        duration: Seconds to animate movement (0 = instant)
    
    Returns:
        dict: {success, x, y}
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return {"success": True, "x": x, "y": y}
    except pyautogui.FailSafeException:
        return {"success": False, "error": "Failsafe triggered — mouse hit screen corner"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def click(x: int, y: int, duration: float = 0.2) -> dict:
    """
    Move to (x, y) and left-click.
    YELLOW tier — requires voice confirmation before calling.
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        time.sleep(0.05)
        pyautogui.click()
        return {"success": True, "action": "click", "x": x, "y": y}
    except pyautogui.FailSafeException:
        return {"success": False, "error": "Failsafe triggered — mouse hit screen corner"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def double_click(x: int, y: int, duration: float = 0.2) -> dict:
    """
    Move to (x, y) and double-click.
    YELLOW tier.
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        time.sleep(0.05)
        pyautogui.doubleClick()
        return {"success": True, "action": "double_click", "x": x, "y": y}
    except pyautogui.FailSafeException:
        return {"success": False, "error": "Failsafe triggered — mouse hit screen corner"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def right_click(x: int, y: int, duration: float = 0.2) -> dict:
    """
    Move to (x, y) and right-click.
    YELLOW tier.
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        time.sleep(0.05)
        pyautogui.rightClick()
        return {"success": True, "action": "right_click", "x": x, "y": y}
    except pyautogui.FailSafeException:
        return {"success": False, "error": "Failsafe triggered — mouse hit screen corner"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def scroll(x: int, y: int, clicks: int, duration: float = 0.2) -> dict:
    """
    Move to (x, y) and scroll.
    
    Args:
        clicks: Positive = scroll up, negative = scroll down
    
    YELLOW tier.
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        time.sleep(0.05)
        pyautogui.scroll(clicks)
        direction = "up" if clicks > 0 else "down"
        return {"success": True, "action": "scroll", "x": x, "y": y, "direction": direction, "clicks": abs(clicks)}
    except pyautogui.FailSafeException:
        return {"success": False, "error": "Failsafe triggered — mouse hit screen corner"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> dict:
    """
    Click and drag from (x1, y1) to (x2, y2).
    YELLOW tier.
    """
    try:
        pyautogui.moveTo(x1, y1, duration=0.2)
        time.sleep(0.05)
        pyautogui.dragTo(x2, y2, duration=duration, button="left")
        return {"success": True, "action": "drag", "from": [x1, y1], "to": [x2, y2]}
    except pyautogui.FailSafeException:
        return {"success": False, "error": "Failsafe triggered — mouse hit screen corner"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def position() -> dict:
    """
    Get current cursor position. GREEN tier — read only.
    """
    pos = pyautogui.position()
    return {"x": pos.x, "y": pos.y}


if __name__ == "__main__":
    import time

    print("Testing cursor module...")
    print(f"Current position: {position()}")

    print("Moving to center of screen in 2 seconds...")
    time.sleep(2)
    result = move(735, 478)
    print(f"Move result: {result}")

    print("Done. Failsafe is ON — move mouse to top-left corner to abort any runaway action.")