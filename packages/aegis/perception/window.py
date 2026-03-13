"""
aegis/screen/window.py
Active window tracking for macOS using Quartz/AppKit.
Provides the bounds of the frontmost window for foveated vision.
"""

import logging

logger = logging.getLogger("aegis.screen.window")

def get_active_window_bounds() -> dict | None:
    """
    Get the bounds of the currently focused (frontmost) window on macOS.

    Returns:
        dict with keys:
            - app_name: str (e.g. "Google Chrome")
            - title: str (window title, may be empty)
            - x: int (left edge, in points)
            - y: int (top edge, in points)
            - width: int (window width, in points)
            - height: int (window height, in points)
        Or None if detection fails.
    """
    try:
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGWindowListOptionOnScreenOnly,
            kCGWindowListExcludeDesktopElements,
            kCGNullWindowID,
        )
        from AppKit import NSWorkspace

        # Get the frontmost application
        active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if not active_app:
            logger.warning("No frontmost application detected.")
            return None

        active_pid = active_app.processIdentifier()
        app_name = active_app.localizedName() or "Unknown"

        # Get all on-screen windows
        window_list = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
            kCGNullWindowID,
        )

        if not window_list:
            logger.warning("No windows found on screen.")
            return None

        # Find the topmost window belonging to the active app
        for window in window_list:
            owner_pid = window.get("kCGWindowOwnerPID", -1)
            if owner_pid != active_pid:
                continue

            # Skip windows with no bounds or zero area
            bounds = window.get("kCGWindowBounds")
            if not bounds:
                continue

            w = int(bounds.get("Width", 0))
            h = int(bounds.get("Height", 0))
            if w <= 0 or h <= 0:
                continue

            # Skip tiny utility windows (e.g., menu bar items)
            if w < 100 or h < 100:
                continue

            title = window.get("kCGWindowName", "") or ""

            result = {
                "app_name": app_name,
                "title": title,
                "x": int(bounds.get("X", 0)),
                "y": int(bounds.get("Y", 0)),
                "width": w,
                "height": h,
            }
            logger.info(f"Active window: {app_name} — '{title}' at ({result['x']}, {result['y']}) {w}x{h}")
            return result

        logger.warning(f"No suitable window found for PID {active_pid} ({app_name}).")
        return None

    except ImportError:
        logger.warning("Quartz/AppKit not available. Active window tracking disabled.")
        return None
    except Exception as e:
        logger.error(f"Error detecting active window: {e}")
        return None


def get_all_visible_windows() -> list[dict]:
    """
    Get a list of all visible windows on screen.

    Returns:
        List of dicts, each with:
            - app_name: str
            - title: str
            - x, y, width, height: int
    """
    try:
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGWindowListOptionOnScreenOnly,
            kCGWindowListExcludeDesktopElements,
            kCGNullWindowID,
        )

        window_list = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
            kCGNullWindowID,
        )

        if not window_list:
            return []

        results = []
        for window in window_list:
            bounds = window.get("kCGWindowBounds")
            if not bounds:
                continue

            w = int(bounds.get("Width", 0))
            h = int(bounds.get("Height", 0))
            if w < 100 or h < 100:
                continue

            app_name = window.get("kCGWindowOwnerName", "Unknown")
            title = window.get("kCGWindowName", "") or ""

            results.append({
                "app_name": app_name,
                "title": title,
                "x": int(bounds.get("X", 0)),
                "y": int(bounds.get("Y", 0)),
                "width": w,
                "height": h,
            })

        return results

    except ImportError:
        logger.warning("Quartz/AppKit not available. Cannot list windows.")
        return []
    except Exception as e:
        logger.error(f"Error listing visible windows: {e}")
        return []
