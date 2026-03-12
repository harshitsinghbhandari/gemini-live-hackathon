import asyncio
import random
import string
import time
import logging
from typing import Optional
import numpy as np
from PIL import ImageGrab
import cv2
import easyocr

logger = logging.getLogger("aegis.screen.ocr")

# Initialize once at module level — never initialize again
reader = easyocr.Reader(['en'])
logger.info("EasyOCR reader initialized")

OCR_CONFIDENCE_THRESHOLD = 0.7
OCR_LOOP_DELAY = 0.5  # seconds to wait after a run finishes before starting next

SCREEN_REGIONS = {
    "top_bar":      lambda y, x, h, w: y < h * 0.05,
    "bottom_bar":   lambda y, x, h, w: y > h * 0.95,
    "left_sidebar": lambda y, x, h, w: h * 0.05 <= y <= h * 0.95 and x < w * 0.15,
    "right_sidebar":lambda y, x, h, w: h * 0.05 <= y <= h * 0.95 and x > w * 0.85,
    "main_content": lambda y, x, h, w: True  # fallback
}


def _generate_id(length: int = 4) -> str:
    """Generate a short alphanumeric ID like 'a3xj'."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _get_region(ymin: int, xmin: int, screen_h: int, screen_w: int) -> str:
    """Classify a coordinate into a screen region."""
    for region_name, condition in SCREEN_REGIONS.items():
        if condition(ymin, xmin, screen_h, screen_w):
            return region_name
    return "main_content"


def _run_ocr_sync() -> dict:
    """
    Synchronous OCR run. Called via asyncio.to_thread to avoid blocking the event loop.
    Returns a structured cache dict ready to store in AegisContext.
    """
    screenshot = ImageGrab.grab()
    screen_w, screen_h = screenshot.size

    img = np.array(screenshot)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    raw_results = reader.readtext(img_bgr)

    # Filter by confidence
    filtered = [r for r in raw_results if r[2] >= OCR_CONFIDENCE_THRESHOLD]

    # Build element map and grouped regions
    elements = {}   # id -> full element data (flat lookup for cursor_click)
    regions = {     # region -> list of elements (for get_screen_elements)
        "top_bar": [],
        "bottom_bar": [],
        "left_sidebar": [],
        "right_sidebar": [],
        "main_content": [],
    }

    for bbox, text, confidence in filtered:
        # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        xmin = int(bbox[0][0])
        ymin = int(bbox[0][1])
        xmax = int(bbox[2][0])
        ymax = int(bbox[2][1])

        element_id = _generate_id()
        # Ensure uniqueness
        while element_id in elements:
            element_id = _generate_id()

        element = {
            "id": element_id,
            "text": text,
            "ymin": ymin,
            "ymax": ymax,
            "xmin": xmin,
            "xmax": xmax,
            "confidence": round(confidence, 3),
        }

        elements[element_id] = element
        region = _get_region(ymin, xmin, screen_h, screen_w)
        regions[region].append({"id": element_id, "text": text})

    return {
        "elements": elements,       # flat dict: id -> full element
        "regions": regions,         # grouped: region_name -> [{id, text}]
        "screen_w": screen_w,
        "screen_h": screen_h,
        "timestamp": time.time(),
        "count": len(elements),
    }


async def ocr_background_loop(context) -> None:
    """
    Infinite background loop. Runs OCR, stores result in context.ocr_cache, waits, repeats.
    Accepts the AegisContext instance as argument.
    Start this with asyncio.create_task(ocr_background_loop(context)) at agent startup.
    Never cancel this task unless the agent is shutting down.
    """
    logger.info("OCR background loop started")
    from aegis.tools.context import window_state

    while True:
        try:
            result = await asyncio.to_thread(_run_ocr_sync)
            context.ocr_cache = result
            # Also update window_state for tool access
            setattr(window_state, 'ocr_cache', result)
            logger.debug(f"OCR cache updated: {result['count']} elements detected")
        except Exception as e:
            logger.error(f"OCR loop error: {e}")
            # Do not crash the loop on error, just wait and retry

        await asyncio.sleep(OCR_LOOP_DELAY)
