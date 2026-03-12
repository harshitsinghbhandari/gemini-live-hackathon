# Aegis — OCR Clicking Pipeline Implementation Spec
> For the precise agent. Follow this exactly, do not deviate, do not add extra features.

---

## Overview

The goal is to fix Gemini's clicking accuracy by replacing coordinate guessing with
OCR-based element identification. Gemini will no longer estimate where things are on
screen — it will look up elements by ID from an OCR cache.

**Files touched:**
- `aegis/screen/ocr.py` — NEW FILE
- `aegis/context.py` — MODIFY
- `aegis/tools/screen_tools.py` — MODIFY (add new tool)
- `aegis/tools/cursor_tools.py` — MODIFY (add label_id param)
- `aegis/prompt.py` — MODIFY (update system instruction)

---

## 1. `aegis/screen/ocr.py` — NEW FILE

### Purpose
Runs EasyOCR in a background asyncio loop. Initializes the reader once at startup.
Stores the latest result into `AegisContext.ocr_cache`. Nothing else reads or writes
to this cache except this file (writes) and the tools (reads).

### Exact implementation

```python
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

    while True:
        try:
            result = await asyncio.to_thread(_run_ocr_sync)
            context.ocr_cache = result
            logger.debug(f"OCR cache updated: {result['count']} elements detected")
        except Exception as e:
            logger.error(f"OCR loop error: {e}")
            # Do not crash the loop on error, just wait and retry

        await asyncio.sleep(OCR_LOOP_DELAY)
```

### Notes for the agent
- Do NOT call `easyocr.Reader()` anywhere else in the codebase. It is initialized here once.
- `asyncio.to_thread` is mandatory — `readtext` is blocking and will freeze the event loop otherwise.
- The loop uses `while True` with a try/except — it must never crash permanently.
- `OCR_LOOP_DELAY = 0.5` means it waits 0.5s after finishing before starting again. Since OCR takes ~6.5s, effective frequency is ~7s per cycle.

---

## 2. `aegis/context.py` — MODIFY

### What to add
Add one field to the `AegisContext` dataclass:

```python
ocr_cache: dict = None
```

### Exact placement
Add it alongside the existing fields in the dataclass. Example of what the dataclass
should look like after modification (do not remove any existing fields):

```python
@dataclass
class AegisContext:
    # ... all existing fields stay exactly as they are ...
    ocr_cache: dict = None  # ADD THIS LINE — populated by aegis.screen.ocr background loop
```

### Notes for the agent
- `dict = None` is intentional. The cache starts empty and tools must handle `None` gracefully.
- Do not add any methods or properties. Just the field.

---

## 3. `aegis/tools/screen_tools.py` — MODIFY

### What to add
Add a new tool class `GetScreenElementsTool` to this file. Do not modify any existing tools.

### Exact implementation

```python
class GetScreenElementsTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_screen_elements"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Returns OCR-detected text elements on screen with their IDs and positions. "
                "Use this BEFORE calling cursor_click to find the label_id of what you want to click. "
                "Filter by region to reduce tokens. Available regions: top_bar, bottom_bar, "
                "left_sidebar, right_sidebar, main_content. "
                "If you need the screenshot image alongside, set image=true."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "enum": ["top_bar", "bottom_bar", "left_sidebar", "right_sidebar", "main_content", "all"],
                        "description": "Which screen region to return elements for. Use 'all' only if unsure."
                    },
                    "image": {
                        "type": "boolean",
                        "description": "If true, also returns a base64 screenshot alongside the JSON. Default false."
                    }
                },
                "required": ["region"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from aegis.context import context  # import the global context instance
        from aegis.screen.capture import capture_screen

        ocr_cache = context.ocr_cache

        # Handle empty cache gracefully
        if ocr_cache is None:
            return {
                "success": False,
                "error": "OCR cache is not ready yet. Wait a moment and try again."
            }

        region = args.get("region", "all")
        include_image = args.get("image", False)

        # Build response elements
        if region == "all":
            result_elements = ocr_cache["regions"]
        else:
            result_elements = {region: ocr_cache["regions"].get(region, [])}

        response = {
            "success": True,
            "elements": result_elements,
            "total_count": ocr_cache["count"],
            "cache_age_seconds": round(time.time() - ocr_cache["timestamp"], 1),
            "screen_w": ocr_cache["screen_w"],
            "screen_h": ocr_cache["screen_h"],
        }

        if include_image:
            screenshot = await asyncio.to_thread(capture_screen)
            response["image"] = screenshot.get("base64", None)

        return response
```

### Notes for the agent
- Add `import time` and `import asyncio` at the top of the file if not already present.
- Register this tool in `aegis/tools/__init__.py` exactly the same way other tools are registered.
- The `capture_screen` import is lazy (inside execute) to avoid circular imports.

---

## 4. `aegis/tools/cursor_tools.py` — MODIFY

### What to change in `CursorClickTool`
Two changes only:
1. Add `label_id` as an optional parameter in the declaration
2. Add ID lookup logic at the top of `execute` — if `label_id` is provided, get coordinates from cache and override `box_2d`

### Exact declaration change
Add this to the `properties` dict in the existing declaration, alongside `box_2d`:

```python
"label_id": {
    "type": "string",
    "description": (
        "The ID of the element to click, obtained from get_screen_elements. "
        "If provided, coordinates are looked up automatically — do not also provide box_2d."
    )
}
```

Change `required` from `["box_2d", "description"]` to `["description"]` —
both `label_id` and `box_2d` are now optional but one must be present (handled in execute).

### Exact execute change
Add this block at the very top of the `execute` method, before any existing logic:

```python
from aegis.context import context  # import global context instance

# If label_id is provided, look up coordinates from OCR cache
if "label_id" in args:
    label_id = args["label_id"]
    ocr_cache = context.ocr_cache

    if ocr_cache is None:
        return {"success": False, "error": "OCR cache not ready. Try again in a moment."}

    element = ocr_cache["elements"].get(label_id)
    if element is None:
        return {
            "success": False,
            "error": f"label_id '{label_id}' not found in OCR cache. Cache may have refreshed. Call get_screen_elements again."
        }

    # Override box_2d with coordinates from cache
    # Convert to 0-1000 scale to match existing get_noisy_center logic
    screen_w = ocr_cache["screen_w"]
    screen_h = ocr_cache["screen_h"]
    args["box_2d"] = [
        int(element["ymin"] / screen_h * 1000),
        int(element["xmin"] / screen_w * 1000),
        int(element["ymax"] / screen_h * 1000),
        int(element["xmax"] / screen_w * 1000),
    ]
    logger.debug(f"label_id '{label_id}' resolved to '{element['text']}' at box_2d {args['box_2d']}")
```

### Notes for the agent
- Do not touch any other logic in `execute` after this block. Everything else runs as before.
- The coordinate conversion to 0-1000 scale is intentional — `get_noisy_center` expects that scale.
- If neither `label_id` nor `box_2d` is in args, the existing check `if "box_2d" not in args` will catch it and return an error as before.

---

## 5. `aegis/prompt.py` — MODIFY

### What to change
Find the `SYSTEM_INSTRUCTION` string and add the following block to it.
Add it in a logical place — after existing tool usage instructions, before any closing remarks.
Do not remove or rewrite any existing instructions.

### Exact text to add

```
CLICKING INSTRUCTIONS:
Before clicking any element on screen, you MUST call get_screen_elements first.
- Use the region parameter to narrow down where the element likely is. For example,
  if clicking a menu item use region="top_bar". If clicking a button in a form use
  region="main_content". Use region="all" only if you are unsure.
- From the returned elements list, find the element whose text matches what you want
  to click. Use its "id" field as the label_id in cursor_click.
- Always pass label_id to cursor_click. Never guess box_2d coordinates.
- If cursor_click returns an error saying label_id not found, the cache has refreshed.
  Call get_screen_elements again to get fresh IDs before retrying.
- Only fall back to box_2d if get_screen_elements returns no relevant elements at all.
```

---

## 6. Agent Startup — MODIFY `main.py` or wherever `AegisVoiceAgent` initializes

### What to add
Start the OCR background loop as an asyncio task during agent startup.

### Exact change
Find where the agent's async tasks are started (likely in `voice.py` or `main.py`).
Add this alongside the other `asyncio.create_task` calls:

```python
from aegis.screen.ocr import ocr_background_loop
from aegis.context import context

asyncio.create_task(ocr_background_loop(context), name="OCRBackgroundLoop")
```

### Notes for the agent
- This task must start AFTER the event loop is running — inside an `async` function, not at module level.
- Do not await it. It runs forever in the background.
- If the agent has a shutdown sequence, cancel this task by name: `OCRBackgroundLoop`.

---

## Summary of all changes

| File | Type | What changes |
|---|---|---|
| `aegis/screen/ocr.py` | NEW | Full OCR background service |
| `aegis/context.py` | MODIFY | Add `ocr_cache: dict = None` field |
| `aegis/tools/screen_tools.py` | MODIFY | Add `GetScreenElementsTool` class + register it |
| `aegis/tools/cursor_tools.py` | MODIFY | Add `label_id` param + cache lookup in `CursorClickTool` |
| `aegis/prompt.py` | MODIFY | Add clicking instructions to `SYSTEM_INSTRUCTION` |
| `main.py` | MODIFY | Start `ocr_background_loop` as asyncio task at startup |

## What is explicitly OUT OF SCOPE for this task
- Action verification (SSIM, perceptual hash) — do not implement
- Browser vs screen demarcation — do not implement
- Qwen / any other vision model — do not implement
- Any changes to `gate.py`, `classifier.py`, `auth.py`, `voice.py` — do not touch
- Any changes to existing tools other than `CursorClickTool` — do not touch