import asyncio
import base64
import io
import logging
from PIL import ImageGrab
from . import config

logger = logging.getLogger("aegis.screen")

async def capture_screen() -> str:
    """Captures screen and returns base64 JPEG"""
    try:
        # ImageGrab.grab() is a blocking call, run in thread
        screenshot = await asyncio.to_thread(ImageGrab.grab)
        screenshot = screenshot.resize((1280, 720))  # resize for token efficiency
        if screenshot.mode == "RGBA":
            screenshot = screenshot.convert("RGB")

        buffer = io.BytesIO()
        screenshot.save(buffer, format="JPEG", quality=60)
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        logger.error(f"Failed to capture screen: {e}")
        return ""

async def screen_stream(interval: float = None):
    """Yields screenshots at regular intervals"""
    if interval is None:
        interval = config.SCREENSHOT_INTERVAL

    while True:
        frame = await capture_screen()
        if frame:
            yield frame
        await asyncio.sleep(interval)
