"""
aegis/screen/cursor.py
Mouse control: move, click, double-click, right-click, scroll.
All actions are intentionally explicit — no magic, no retries.
"""

import time
import pyautogui
import logging

logger = logging.getLogger(__name__)

# Safety: pyautogui will raise an exception if mouse hits screen corner
# This is a good failsafe — keeps the user in control
pyautogui.FAILSAFE = True

# Small delay between actions — makes automation look natural and reduces errors
pyautogui.PAUSE = 0.05


def get_retina_scale() -> float:
    """Detect macOS backing scale factor (usually 2.0 for Retina)."""
    try:
        import AppKit
        return AppKit.NSScreen.mainScreen().backingScaleFactor()
    except Exception:
        logger.info(f"using fallback scale factor 2.0")
        return 2.0  # Fallback

def nudge(offset_x: int, offset_y: int, duration: float = 0.2) -> dict:
    """
    Move the cursor relative to its current position by (offset_x, offset_y) pixels.
    GREEN/YELLOW tier - useful for precision nudging without recalculating entirely.
    """
    try:
        logger.debug(f"Nudging cursor by ({offset_x}, {offset_y})")
        pyautogui.moveRel(offset_x, offset_y, duration=duration)
        pos = pyautogui.position()
        return {"success": True, "action": "nudge", "x": pos.x, "y": pos.y}
    except pyautogui.FailSafeException:
        logger.warning("Failsafe triggered during nudge")
        return {"success": False, "error": "Failsafe triggered — mouse hit screen corner"}
    except Exception as e:
        return {"success": False, "error": str(e)}

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
        logger.info(f"Moving cursor to ({x}, {y}) with duration {duration}")
        pyautogui.moveTo(x, y, duration=duration,tween=pyautogui.easeOutElastic)
        return {"success": True, "x": x, "y": y}
    except pyautogui.FailSafeException:
        logger.warning("Failsafe triggered during move")
        return {"success": False, "error": "Failsafe triggered — mouse hit screen corner"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def click(x: int, y: int, duration: float = 0.2) -> dict:
    """
    Move to (x, y) and left-click.
    YELLOW tier — requires voice confirmation before calling.
    """
    try:
        logger.info(f"Clicking at ({x}, {y}) with duration {duration}")
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
        logger.info(f"Double clicking at ({x}, {y}) with duration {duration}")
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
        logger.info(f"Right clicking at ({x}, {y}) with duration {duration}")
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
        logger.info(f"Scrolling at ({x}, {y}) with duration {duration}")
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
        logger.info(f"Dragging from ({x1}, {y1}) to ({x2}, {y2}) with duration {duration}")
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
    logger.info(f"Current cursor position: ({pos.x}, {pos.y})")
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