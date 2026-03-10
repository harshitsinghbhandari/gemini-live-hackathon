import base64
import json
import logging
import pyautogui
from google.genai import types
from .gate import gate_action
from .screen.capture import capture_screen

logger = logging.getLogger("aegis.computer_use")

def denormalize(x: int, y: int) -> tuple[int, int]:
    """Convert Gemini 0-1000 coordinates to dynamic screen bounds with Retina support."""
    try:
        # Use AppKit to get precise logical coordinates (points) on macOS
        from AppKit import NSScreen
        screen = NSScreen.mainScreen()
        screen_w = screen.frame().size.width
        screen_h = screen.frame().size.height
        scale = screen.backingScaleFactor()
    except Exception:
        # Fallback to pyautogui for non-macOS or if AppKit fails
        screen_w, screen_h = pyautogui.size()
        scale = 1.0

    nx = max(0, min(1000, x))
    ny = max(0, min(1000, y))

    # Calculate target in points.
    # If scale=2.0 (Retina), pyautogui's moveTo(x, y) expects logical coordinates (points),
    # which we already calculated using NSScreen frame size.
    dx, dy = int(nx / 1000 * screen_w), int(ny / 1000 * screen_h)

    logger.info(f"📍 Scaling: ({x}, {y}) -> ({dx}, {dy}) on screen {screen_w}x{screen_h} (scale={scale})")
    return dx, dy

async def handle_computer_use(fn, agent_context, update_status_fn):
    """
    Translates Gemini's native ComputerUse action into Aegis screen tools.
    """
    logger.info(f"🖥️  ComputerUse Action: {fn.name}")
    logger.info(f"   Original Args: {json.dumps(fn.args)}")
    
    mapped_tool = None
    mapped_args = {}
    
    if fn.name == "open_web_browser":
        mapped_tool = "keyboard_hotkey"
        mapped_args = {"keys": ["command", "space"]} # Spotlight
    elif fn.name == "navigate":
        mapped_tool = "keyboard_type"
        mapped_args = {"text": fn.args.get("url", ""), "press_enter": True}
    elif fn.name == "click_at":
        mapped_tool = "cursor_click"
        mapped_args["x"], mapped_args["y"] = denormalize(fn.args["x"], fn.args["y"])
        mapped_args["description"] = f"Click at ({fn.args['x']}, {fn.args['y']})"
    elif fn.name == "double_click_at":
        mapped_tool = "cursor_double_click"
        mapped_args["x"], mapped_args["y"] = denormalize(fn.args["x"], fn.args["y"])
        mapped_args["description"] = f"Double-click at ({fn.args['x']}, {fn.args['y']})"
    elif fn.name == "right_click_at":
        mapped_tool = "cursor_right_click"
        mapped_args["x"], mapped_args["y"] = denormalize(fn.args["x"], fn.args["y"])
        mapped_args["description"] = f"Right-click at ({fn.args['x']}, {fn.args['y']})"
    elif fn.name == "drag_and_drop":
        mapped_tool = "cursor_drag"
        mapped_args["x1"], mapped_args["y1"] = denormalize(fn.args["x1"], fn.args["y1"])
        mapped_args["x2"], mapped_args["y2"] = denormalize(fn.args["x2"], fn.args["y2"])
    elif fn.name == "scroll":
        mapped_tool = "cursor_scroll"
        mapped_args["x"], mapped_args["y"] = denormalize(fn.args["x"], fn.args["y"])
        mapped_args["clicks"] = -10 if fn.args.get("direction") == "down" else 10
    elif fn.name == "type_text_at":
        mapped_tool = "keyboard_type"
        tx, ty = denormalize(fn.args["x"], fn.args["y"])
        logger.info(f"⌨️  Type-at: Clicking ({tx}, {ty}) before typing '{fn.args.get('text', '')}'")
        await gate_action(f"Click at ({tx}, {ty})", agent_context, tool_name="cursor_click", tool_args={"x": tx, "y": ty, "description": "Focus before typing"})
        mapped_args = {"text": fn.args.get("text", "")}
    elif fn.name == "key_combination":
        mapped_tool = "keyboard_hotkey"
        mapped_args = {"keys": fn.args.get("keys", [])}
    elif fn.name == "wait":
        mapped_tool = "cursor_move"
        mapped_args = {"x": 735, "y": 478}

    if not mapped_tool:
        logger.warning(f"⚠️  No mapping found for ComputerUse action: {fn.name}")
        return None

    simulated_action = f"ComputerUse: {fn.name} with args {json.dumps(fn.args)}"
    logger.info(f"🛡️  Gating simulated action: {simulated_action}")
    result = await gate_action(
        simulated_action, agent_context,
        tool_name=mapped_tool,
        tool_args=mapped_args,
        on_auth_request=update_status_fn,
        call_id=fn.id
    )
    
    logger.info(f"   Gate Result: {result.get('success', False)} - {result.get('error', 'No error')}")
    
    shot = capture_screen()
    response_payload = {"url": "macOS Desktop"}
    if not result.get("success"):
        response_payload["error"] = result.get("error", "Action blocked or failed")
    
    f_resp = types.FunctionResponse(
        id=fn.id,
        name=fn.name,
        response=response_payload
    )
    
    # Return the response and the screenshot data for the caller to send
    return f_resp, shot
