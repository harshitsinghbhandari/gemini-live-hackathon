import logging
import random
import pyautogui
from .. import config
from ..screen.capture import capture_screen, capture_region

logger = logging.getLogger("aegis.tools.context")

class WindowContext:
    def __init__(self):
        self.crop_origin_x = 0
        self.crop_origin_y = 0
        self.crop_width = None
        self.crop_height = None
        self.last_target_x = None
        self.last_target_y = None
        self.active_session_lock = False

window_state = WindowContext()

def reset_view(context=None):
    window_state.crop_origin_x = 0
    window_state.crop_origin_y = 0
    window_state.crop_width = None
    window_state.crop_height = None
    if context:
        context.execution_plan = None
        context.plan_index = 0

def get_current_view():
    """Returns a full screenshot, or a zoomed-in crop if screen_crop is active."""
    if window_state.crop_width is not None and window_state.crop_height is not None:
        px = int(window_state.crop_origin_x)
        py = int(window_state.crop_origin_y)
        pw = int(window_state.crop_width)
        ph = int(window_state.crop_height)
        return capture_region(px, py, pw, ph)
    else:
        return capture_screen()

def get_noisy_center(box):
    """Calculate center of [ymin, xmin, ymax, xmax] with random noise."""
    ymin, xmin, ymax, xmax = box
    # 1. Normalized center
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    # 2. Add noise (+- 5 normalized units)
    cx += random.uniform(-5, 5)
    cy += random.uniform(-5, 5)
    # 3. Clamp to 0-1000
    cx = max(0, min(1000, cx))
    cy = max(0, min(1000, cy))
    
    # 4. Handle Foveated Vision (Crop offset mapping)
    if window_state.crop_width is not None and window_state.crop_height is not None:
        logical_x = window_state.crop_origin_x + (cx / 1000) * window_state.crop_width
        logical_y = window_state.crop_origin_y + (cy / 1000) * window_state.crop_height
    else:
        screen_w, screen_h = pyautogui.size()
        logical_x = (cx / 1000) * screen_w
        logical_y = (cy / 1000) * screen_h
    
    target_x = int(logical_x)
    target_y = int(logical_y)
    
    return target_x, target_y
