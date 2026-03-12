import asyncio
import hashlib
import logging
from typing import Any, Dict

from .base import BaseTool, registry
from .context import get_noisy_center, window_state
from ..screen.cursor import (
    move, click, double_click, right_click, scroll, drag, position, nudge
)
from ..screen.capture import capture_region

class CursorMoveTool(BaseTool):
    @property
    def name(self) -> str:
        return "cursor_move"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Move the cursor to a specific bounding box center without clicking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                    }
                },
                "required": ["box_2d"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "box_2d" not in args:
            return {"success": False, "error": "Missing required argument: box_2d"}
        cx, cy = get_noisy_center(args["box_2d"])
        return move(int(cx), int(cy))

class CursorClickTool(BaseTool):
    @property
    def name(self) -> str:
        return "cursor_click"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Move cursor to bounding box center and left-click. Use screen_capture first to determine correct coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                    },
                    "label_id": {
                        "type": "string",
                        "description": (
                            "The ID of the element to click, obtained from get_screen_elements. "
                            "If provided, coordinates are looked up automatically — do not also provide box_2d."
                        )
                    },
                    "description": {"type": "string", "description": "What you are clicking on, e.g. 'Submit button', 'Chrome icon'"}
                },
                "required": ["description"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from .context import window_state as context  # import global context instance

        # If label_id is provided, look up coordinates from OCR cache
        if "label_id" in args:
            label_id = args["label_id"]
            ocr_cache = getattr(context, 'ocr_cache', None)

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
            logger = logging.getLogger("aegis.tools.cursor")
            logger.debug(f"label_id '{label_id}' resolved to '{element['text']}' at box_2d {args['box_2d']}")

        if "box_2d" not in args:
            return {"success": False, "error": "Missing required argument: box_2d or label_id"}
        cx, cy = get_noisy_center(args["box_2d"])
        
        # OBSERVE: Capture pixel hash of target region before click
        try:
            region_before = capture_region(max(0, int(cx) - 75), max(0, int(cy) - 75), 150, 150)
            hash_before = hashlib.md5(region_before["base64"].encode()).hexdigest()
        except Exception:
            hash_before = None
        
        result = click(int(cx), int(cy))
        
        # VERIFY: Re-capture after 300ms and compare
        if hash_before:
            await asyncio.sleep(0.3)
            try:
                region_after = capture_region(max(0, int(cx) - 75), max(0, int(cy) - 75), 150, 150)
                hash_after = hashlib.md5(region_after["base64"].encode()).hexdigest()
                result["diff_detected"] = hash_before != hash_after
                result["state_before"] = hash_before[:8]
                result["state_after"] = hash_after[:8]
            except Exception:
                result["diff_detected"] = None
        
        return result

class CursorDoubleClickTool(BaseTool):
    @property
    def name(self) -> str:
        return "cursor_double_click"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Move cursor to bounding box center and double-click.",
            "parameters": {
                "type": "object",
                "properties": {
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                    },
                    "description": {"type": "string", "description": "What you are double-clicking on"}
                },
                "required": ["box_2d", "description"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "box_2d" not in args:
            return {"success": False, "error": "Missing required argument: box_2d"}
        cx, cy = get_noisy_center(args["box_2d"])
        return double_click(int(cx), int(cy))

class CursorRightClickTool(BaseTool):
    @property
    def name(self) -> str:
        return "cursor_right_click"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Move cursor to bounding box center and right-click to open context menu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                    },
                    "description": {"type": "string", "description": "What you are right-clicking on"}
                },
                "required": ["box_2d", "description"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "box_2d" not in args:
            return {"success": False, "error": "Missing required argument: box_2d"}
        cx, cy = get_noisy_center(args["box_2d"])
        return right_click(int(cx), int(cy))

class CursorScrollTool(BaseTool):
    @property
    def name(self) -> str:
        return "cursor_scroll"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Scroll up or down at a specific bounding box center.",
            "parameters": {
                "type": "object",
                "properties": {
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[ymin, xmin, ymax, xmax] (0-1000 scale)"
                    },
                    "clicks": {
                        "type": "integer",
                        "description": "Number of scroll clicks. Positive = up, negative = down. Use 3-5 for normal scroll."
                    }
                },
                "required": ["box_2d", "clicks"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "box_2d" not in args or "clicks" not in args:
            return {"success": False, "error": "Missing required arguments: box_2d, clicks"}
        cx, cy = get_noisy_center(args["box_2d"])
        return scroll(int(cx), int(cy), args["clicks"])

class CursorDragTool(BaseTool):
    @property
    def name(self) -> str:
        return "cursor_drag"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Click and drag from one coordinate to another.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1": {"type": "integer", "description": "Start X coordinate"},
                    "y1": {"type": "integer", "description": "Start Y coordinate"},
                    "x2": {"type": "integer", "description": "End X coordinate"},
                    "y2": {"type": "integer", "description": "End Y coordinate"}
                },
                "required": ["x1", "y1", "x2", "y2"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if any(k not in args for k in ["x1", "y1", "x2", "y2"]):
            return {"success": False, "error": "Missing required arguments: x1, y1, x2, y2"}
        return drag(args["x1"], args["y1"], args["x2"], args["y2"])

class CursorNudgeTool(BaseTool):
    @property
    def name(self) -> str:
        return "cursor_nudge"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Move the cursor relative to its current position by exact pixels. Useful for fine-grained correction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "offset_x": {"type": "integer", "description": "Pixel adjustment on X axis (positive=right, negative=left)"},
                    "offset_y": {"type": "integer", "description": "Pixel adjustment on Y axis (positive=down, negative=up)"}
                },
                "required": ["offset_x", "offset_y"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "offset_x" not in args or "offset_y" not in args:
            return {"success": False, "error": "Missing required arguments: offset_x, offset_y"}
        return nudge(args["offset_x"], args["offset_y"])

class CursorTargetTool(BaseTool):
    @property
    def name(self) -> str:
        return "cursor_target"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Show a red target overlay at the specified bounding box and return a Verification Snapshot. Use this to verify accuracy BEFORE clicking. Follow up with cursor_confirm_click or cursor_nudge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[ymin, xmin, ymax, xmax] (0-1000 scale) to target"
                    }
                },
                "required": ["box_2d"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if "box_2d" not in args:
            return {"success": False, "error": "Missing required argument: box_2d"}
        
        px, py = get_noisy_center(args["box_2d"])
        
        # AppKit overlay inherently accepts logical coordinates
        import subprocess, sys, os
        from ..screen_executor import __file__ as screen_executor_file
        script_path = os.path.join(os.path.dirname(screen_executor_file), "screen", "overlay.py")
        subprocess.Popen([sys.executable, script_path, str(int(px)), str(int(py)), "30", "1500"])
        
        # Allow time for window to appear
        await asyncio.sleep(0.15)
        
        # Set a 200x200 crop around the target for the verification snapshot
        window_state.crop_origin_x = max(0, px - 100)
        window_state.crop_origin_y = max(0, py - 100)
        window_state.crop_width = 200
        window_state.crop_height = 200
        
        window_state.last_target_x = px
        window_state.last_target_y = py
        
        return {
            "success": True,
            "action": self.name,
            "message": "Red target drawn. A verification thumbnail will be returned in the next turn. If perfectly centered, use cursor_confirm_click."
        }

class CursorConfirmClickTool(BaseTool):
    @property
    def name(self) -> str:
        return "cursor_confirm_click"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Click exactly where the red target overlay was last placed.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if window_state.last_target_x is None or window_state.last_target_y is None:
            return {"success": False, "error": "No target set. Use cursor_target first."}
        return click(int(window_state.last_target_x), int(window_state.last_target_y))

# Register all tools
registry.register(CursorMoveTool())
registry.register(CursorClickTool())
registry.register(CursorDoubleClickTool())
registry.register(CursorRightClickTool())
registry.register(CursorScrollTool())
registry.register(CursorDragTool())
registry.register(CursorNudgeTool())
registry.register(CursorTargetTool())
registry.register(CursorConfirmClickTool())
