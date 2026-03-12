"""
aegis/screen/capture.py
Captures screenshots and encodes them for Gemini multimodal input.
"""

import base64
import io
from PIL import Image
import mss
import mss.tools
import logging

logger = logging.getLogger(__name__)


def get_native_som_elements() -> list[dict]:
    """
    Extract interactive elements from the frontmost application using macOS Accessibility API.
    """
    try:
        from AppKit import NSWorkspace
        from Quartz import (
            AXUIElementCreateApplication,
            AXUIElementCopyAttributeValue,
            kAXChildrenAttribute,
            kAXRoleAttribute,
            kAXPositionAttribute,
            kAXSizeAttribute,
            kAXTitleAttribute,
            kAXRoleDescriptionAttribute,
            kAXEnabledAttribute
        )
        import objc

        active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if not active_app:
            return []

        app_ref = AXUIElementCreateApplication(active_app.processIdentifier())
        
        elements = []
        id_counter = 1

        def traverse(el, depth=0):
            nonlocal id_counter
            if depth > 5 or len(elements) > 50:
                return

            # Get Role
            err, role = AXUIElementCopyAttributeValue(el, kAXRoleAttribute, None)
            if err == 0 and role in ["AXButton", "AXTextField", "AXCheckBox", "AXMenuItem", "AXRadioButton", "AXComboBox"]:
                # Get Position and Size
                err_p, pos = AXUIElementCopyAttributeValue(el, kAXPositionAttribute, None)
                err_s, size = AXUIElementCopyAttributeValue(el, kAXSizeAttribute, None)
                
                if err_p == 0 and err_s == 0:
                    # pos and size are opaque C types, we need to extract x, y, w, h
                    # Quartz provides helper functions or we can use objc bridge
                    try:
                        # Simple heuristic for bounding box
                        x = pos.x if hasattr(pos, 'x') else 0
                        y = pos.y if hasattr(pos, 'y') else 0
                        w = size.width if hasattr(size, 'width') else 0
                        h = size.height if hasattr(size, 'height') else 0
                        
                        if w > 5 and h > 5:
                            elements.append({
                                "id": id_counter,
                                "type": "native",
                                "role": role,
                                "bbox": {"x": x, "y": y, "w": w, "h": h},
                                "ref": el
                            })
                            id_counter += 1
                    except Exception:
                        pass

            # Recurse children
            err, children = AXUIElementCopyAttributeValue(el, kAXChildrenAttribute, None)
            if err == 0 and children:
                for child in children:
                    traverse(child, depth + 1)

        traverse(app_ref)
        return elements

    except Exception as e:
        logger.error(f"Native SoM extraction failed: {e}")
        return []

def capture_screen(monitor: int = 1, scale_to: tuple = (1470, 956), quality: int = 70, som: bool = False) -> dict:
    """
    Capture the full screen and return as base64-encoded JPEG.
    """
    logger.info(f"Capturing screen (monitor={monitor}, scale={scale_to}, quality={quality}, som={som})")
    with mss.mss() as sct:
        mon = sct.monitors[monitor]
        screenshot = sct.grab(mon)

        # Convert to PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        
        native_elements = []
        if som:
            from .som import draw_som_labels
            native_elements = get_native_som_elements()
            img = draw_som_labels(img, native_elements)

        # Scale down if needed
        if scale_to and img.size != scale_to:
            img = img.resize(scale_to, Image.BILINEAR)

        # Encode as JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)

        encoded = base64.b64encode(buffer.read()).decode("utf-8")

        return {
            "base64": encoded,
            "mime_type": "image/jpeg",
            "width": img.width,
            "height": img.height,
            "som_elements": native_elements if som else []
        }


def capture_region(x: int, y: int, width: int, height: int) -> dict:
    """
    Capture a specific region of the screen.
    Useful for zooming into a specific UI element after initial scan.
    
    Returns same dict format as capture_screen.
    """
    with mss.mss() as sct:
        region = {"top": y, "left": x, "width": width, "height": height}
        screenshot = sct.grab(region)

        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        encoded = base64.b64encode(buffer.read()).decode("utf-8")

        return {
            "base64": encoded,
            "mime_type": "image/jpeg",
            "width": img.width,
            "height": img.height,
        }


def capture_active_window(padding: int = 50, quality: int = 70) -> dict:
    """
    Capture only the active (frontmost) window plus a padding buffer.
    Falls back to full-screen capture if window detection fails.

    Args:
        padding: Pixels to expand around the window bounds for anchoring context.
        quality: JPEG compression quality.

    Returns:
        dict with keys: base64, mime_type, width, height, origin_x, origin_y
        origin_x/origin_y are the top-left of the captured region in screen coords,
        needed for coordinate re-mapping.
    """
    try:
        from .window import get_active_window_bounds

        bounds = get_active_window_bounds()
        if bounds is None:
            logger.info("Active window detection failed, falling back to full screen.")
            shot = capture_screen(quality=quality)
            shot["origin_x"] = 0
            shot["origin_y"] = 0
            return shot

        # Get screen dimensions for clamping
        with mss.mss() as sct:
            mon = sct.monitors[1]
            screen_w = mon["width"]
            screen_h = mon["height"]

        # Expand bounds by padding, clamped to screen edges
        x = max(0, bounds["x"] - padding)
        y = max(0, bounds["y"] - padding)
        x2 = min(screen_w, bounds["x"] + bounds["width"] + padding)
        y2 = min(screen_h, bounds["y"] + bounds["height"] + padding)
        w = x2 - x
        h = y2 - y

        if w <= 0 or h <= 0:
            logger.warning("Invalid active window dimensions after padding, falling back.")
            shot = capture_screen(quality=quality)
            shot["origin_x"] = 0
            shot["origin_y"] = 0
            return shot

        logger.info(f"Capturing active window: {bounds['app_name']} at ({x},{y}) {w}x{h}")

        region_shot = capture_region(x, y, w, h)
        region_shot["origin_x"] = x
        region_shot["origin_y"] = y
        return region_shot

    except Exception as e:
        logger.error(f"Error in capture_active_window: {e}, falling back to full screen.")
        shot = capture_screen(quality=quality)
        shot["origin_x"] = 0
        shot["origin_y"] = 0
        return shot


def capture_as_gemini_part(monitor: int = 1) -> dict:
    """
    Returns screenshot formatted as a Gemini API inline_data part.
    Ready to drop directly into a Gemini messages array.
    
    Usage:
        part = capture_as_gemini_part()
        response = model.generate_content([part, "What do you see?"])
    """
    shot = capture_screen(monitor=monitor)
    return {
        "inline_data": {
            "mime_type": shot["mime_type"],
            "data": shot["base64"],
        }
    }


if __name__ == "__main__":
    # Quick test — saves a screenshot to /tmp/aegis_test.jpg
    print("Capturing screen...")
    shot = capture_screen()
    print(f"Captured: {shot['width']}x{shot['height']}, base64 length: {len(shot['base64'])}")

    # Save to disk to verify it looks right
    img_bytes = base64.b64decode(shot["base64"])
    with open("/tmp/aegis_test.jpg", "wb") as f:
        f.write(img_bytes)
    print("Saved to /tmp/aegis_test.jpg — open it to verify.")