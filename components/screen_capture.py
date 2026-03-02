import asyncio
import base64
from PIL import ImageGrab
import io

async def capture_screen():
    """Captures screen and returns base64 JPEG"""
    screenshot = ImageGrab.grab()
    screenshot = screenshot.resize((1280, 720))  # resize for token efficiency
    if screenshot.mode == "RGBA":
        screenshot = screenshot.convert("RGB")
    buffer = io.BytesIO()
    screenshot.save(buffer, format="JPEG", quality=60)
    return base64.b64encode(buffer.getvalue()).decode()

async def screen_stream(interval=1.0):
    """Yields screenshots at regular intervals"""
    while True:
        frame = await asyncio.to_thread(capture_screen)
        yield frame
        await asyncio.sleep(interval)