import logging
import asyncio
import time
from typing import Any, Dict
from google import genai
from google.genai import types
import base64

from aegis.tools.base import BaseTool, registry
from aegis.tools.context import get_current_view, reset_view, window_state
from configs.agent import config
from configs.agent.config import prompt

logger = logging.getLogger("aegis.tools.screen")

_client = None

def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _client

class ScreenCaptureTool(BaseTool):
    @property
    def name(self) -> str:
        return "screen_capture"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Take a screenshot of the current screen. Use this first before any click or type action to understand what is on screen and get accurate coordinates.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        reset_view()
        # ⚡ Bolt: Offload CPU-bound PIL/mss capture to thread pool
        shot = await asyncio.to_thread(get_current_view)
        return {
            "success": True,
            "action": self.name,
            "width": shot["width"],
            "height": shot["height"],
            "note": "Screenshot captured and available for Gemini analysis"
        }

class ScreenReadTool(BaseTool):
    @property
    def name(self) -> str:
        return "screen_read"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Take a screenshot and describe what is currently visible on screen — apps, windows, text, buttons, and UI elements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Optional specific question about the screen, e.g. 'Where is the search bar?' or 'Is Chrome open?'"
                    }
                },
                "required": []
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes a screenshot and asks Gemini to describe it.
        This tool requires a Gemini API call internally.
        """
        question = args.get("question", prompt.SCREEN_READ_DEFAULT_QUESTION)
        reset_view()
        # ⚡ Bolt: Offload CPU-bound PIL/mss capture to thread pool
        shot = await asyncio.to_thread(get_current_view)

        # ⚡ Bolt: Use globally hoisted genai.Client to avoid instantiation overhead
        client = get_client()
        try:
            response = await client.aio.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(
                        data=base64.b64decode(shot["base64"]),
                        mime_type=shot["mime_type"]
                    ),
                    question
                ]
            )
            return {
                "success": True,
                "action": self.name,
                "description": response.text
            }
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return {"success": False, "error": f"Gemini analysis failed: {str(e)}"}

class ScreenCropTool(BaseTool):
    @property
    def name(self) -> str:
        return "screen_crop"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Request a high-resolution crop of a specific Region of Interest (ROI). Use this to get a clearer view of a small area before clicking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[ymin, xmin, ymax, xmax] (0-1000 scale) of the region to crop"
                    }
                },
                "required": ["box_2d"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "box_2d" not in args:
            return {"success": False, "error": "Missing required argument: box_2d"}
        
        box = args["box_2d"]
        ymin, xmin, ymax, xmax = box
        
        if window_state.crop_width is not None and window_state.crop_height is not None:
            base_x = window_state.crop_origin_x
            base_y = window_state.crop_origin_y
            base_w = window_state.crop_width
            base_h = window_state.crop_height
        else:
            import pyautogui
            base_x = 0
            base_y = 0
            base_w, base_h = pyautogui.size()
            
        x = base_x + (xmin / 1000) * base_w
        y = base_y + (ymin / 1000) * base_h
        w = ((xmax - xmin) / 1000) * base_w
        h = ((ymax - ymin) / 1000) * base_h
        
        # Store logical location for future global-to-local mapping
        window_state.crop_origin_x = x
        window_state.crop_origin_y = y
        window_state.crop_width = w
        window_state.crop_height = h
        
        return {
            "success": True,
            "action": self.name,
            "message": "Crop captured successfully. Use this high-res context for precision actions."
        }


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
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "If true, returns from cache if fresh (<5s). Default true."
                    }
                },
                "required": ["region"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from aegis.tools.context import window_state as context # Use window_state as proxy for ocr_cache
        from aegis.perception.screen.capture import capture_screen

        use_cache = args.get("use_cache", True)
        ocr_cache = getattr(context, 'ocr_cache', None)

        # Trigger on-demand OCR if cache stale or requested
        if not use_cache or ocr_cache is None or (time.time() - ocr_cache["timestamp"] > 5):
            from aegis.perception.screen.ocr import _process_frame
            # We don't have the global context easily here, so we pass None or a dummy
            # ocr_background_loop usually handles the context.
            # For on-demand, we just want the result.
            new_result = await asyncio.to_thread(_process_frame, None)
            if new_result:
                ocr_cache = new_result
                setattr(context, 'ocr_cache', new_result)

        ocr_cache = getattr(context, 'ocr_cache', None)

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


class GetAnnotatedElementsTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_annotated_elements"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Returns a list of screen elements with sequential numeric labels (1-N) for easy selection. Always check this first for label_id clicking.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from aegis.tools.context import window_state as context
        ocr_cache = getattr(context, 'ocr_cache', None)

        if ocr_cache is None:
            return {"success": False, "error": "OCR cache not ready."}

        return {
            "success": True,
            "annotated_elements": ocr_cache.get("annotated_json", []),
            "total_count": ocr_cache["count"],
            "cache_age_seconds": round(time.time() - ocr_cache["timestamp"], 1)
        }


class ClickByWordTool(BaseTool):
    @property
    def name(self) -> str:
        return "click_by_word"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Click an on-screen element by matching its text. Provide the text or description of the button/element "
                "(e.g. 'Login', 'Submit form'). Uses latest annotated elements and fuzzy matching. "
                "Faster and more reliable than coordinate guessing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text or description to match"
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Minimum fuzzy match score (0–100). Default 75.",
                    }
                },
                "required": ["text"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from aegis.tools.context import window_state as context
        from rapidfuzz import process, fuzz

        requested_text = args.get("text")
        threshold = args.get("threshold", 75)

        ocr_cache = getattr(context, 'ocr_cache', None)
        if ocr_cache is None:
            return {
                "success": False,
                "error": "No screen elements available. Call get_screen_elements first to populate the cache."
            }

        # Build choices: mapping label_id to text for all elements that have text
        choices = {
            label_id: el.get("text", "") 
            for label_id, el in ocr_cache.get("elements", {}).items() 
            if el.get("text")
        }

        if not choices:
            return {
                "success": False,
                "error": "No text elements found on screen to match against."
            }

        # Fuzzy match using token_sort_ratio for robustness
        best = process.extractOne(requested_text, choices, scorer=fuzz.token_sort_ratio)

        if not best or best[1] < threshold:
            best_score = best[1] if best else 0
            return {
                "success": False,
                "message": f"No good match for '{requested_text}' (best score: {best_score:.1f})"
            }

        matched_text = best[0]
        score = best[1]
        matched_id = best[2]

        logger.info(f"Fuzzy matched '{requested_text}' -> '{matched_text}' (id={matched_id}, score={score:.1f})")

        # Reuse existing CursorClickTool logic by dispatching through the registry
        click_result = await registry.dispatch("cursor_click", {
            "label_id": matched_id,
            "description": f"Fuzzy clicked element matching '{requested_text}' (found '{matched_text}')"
        })

        return {
            "success": click_result.get("success", False),
            "matched_text": matched_text,
            "matched_id": matched_id,
            "score": score,
            "click_result": click_result
        }


# Register all tools in this module
registry.register(ScreenCaptureTool())
registry.register(ScreenReadTool())
registry.register(ScreenCropTool())
registry.register(GetScreenElementsTool())
registry.register(GetAnnotatedElementsTool())
registry.register(ClickByWordTool())
