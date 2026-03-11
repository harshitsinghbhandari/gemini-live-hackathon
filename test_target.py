import asyncio
import base64
import sys
import os

# Ensure aegis is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aegis.screen_executor import _dispatch, get_current_view, window_state

async def main():
    print("Executing cursor_target...")
    # This should spawn the circle and set the crop origin
    res = await _dispatch("cursor_target", {"box_2d": [450, 450, 550, 550]})
    print(res)
    
    print(f"Window state crop: {window_state.crop_origin_x}, {window_state.crop_origin_y}, w: {window_state.crop_width}, h: {window_state.crop_height}")
    
    print("Getting current view (should be the 200x200 crop)")
    view = get_current_view()
    
    print(f"Captured view size: {view['width']}x{view['height']}")
    
    # Save the base64 to check
    with open("/tmp/test_crop.jpg", "wb") as f:
        f.write(base64.b64decode(view["base64"]))
    print("Saved to /tmp/test_crop.jpg")
    
    # Test cursor_confirm_click
    print("Confirming click...")
    res2 = await _dispatch("cursor_confirm_click", {})
    print(res2)

if __name__ == "__main__":
    asyncio.run(main())
