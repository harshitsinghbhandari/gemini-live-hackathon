"""
aegis/screen/capture.py
Captures screenshots and encodes them for Gemini multimodal input.
"""

import base64
import io
from PIL import Image
import mss
import mss.tools


def capture_screen(monitor: int = 1, scale_to: tuple = (1470, 956), quality: int = 70) -> dict:
    """
    Capture the full screen and return as base64-encoded JPEG.
    
    Args:
        monitor: Monitor index (1 = primary)
        scale_to: Resize to this resolution before encoding (saves tokens)
        quality: JPEG compression quality (1-100)
    
    Returns:
        dict with keys:
            - base64: base64 string (no data URI prefix)
            - mime_type: "image/jpeg"
            - width: actual capture width
            - height: actual capture height
    """
    with mss.mss() as sct:
        mon = sct.monitors[monitor]
        screenshot = sct.grab(mon)

        # Convert to PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        # Scale down if needed (reduces tokens sent to Gemini)
        if scale_to and img.size != scale_to:
            img = img.resize(scale_to, Image.BILINEAR)

        # Encode as JPEG (much smaller than PNG, good enough for UI understanding)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)

        encoded = base64.b64encode(buffer.read()).decode("utf-8")

        return {
            "base64": encoded,
            "mime_type": "image/jpeg",
            "width": img.width,
            "height": img.height,
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