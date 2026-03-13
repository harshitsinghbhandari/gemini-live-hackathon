import sys
import time
import AppKit
import logging

logger = logging.getLogger(__name__)

def draw_red_circle(x, y, radius, duration_ms):
    logger.info(f"Drawing red circle at ({x}, {y}) with radius {radius} for {duration_ms}ms")
    screen_rect = AppKit.NSScreen.mainScreen().frame()
    screen_h = screen_rect.size.height
    
    # Convert top-left origin to bottom-left
    converted_y = screen_h - y
    
    rect = AppKit.NSMakeRect(x - radius, converted_y - radius, radius * 2, radius * 2)
    
    window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        rect,
        AppKit.NSWindowStyleMaskBorderless,
        AppKit.NSBackingStoreBuffered,
        False
    )
    
    window.setOpaque_(False)
    window.setBackgroundColor_(AppKit.NSColor.clearColor())
    window.setLevel_(AppKit.NSStatusWindowLevel)
    window.setIgnoresMouseEvents_(True)
    
    class CircleView(AppKit.NSView):
        def drawRect_(self, dirtyRect):
            AppKit.NSColor.redColor().setStroke()
            path = AppKit.NSBezierPath.bezierPathWithOvalInRect_(self.bounds())
            path.setLineWidth_(4.0)
            path.stroke()
            
    view = CircleView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, radius*2, radius*2))
    window.setContentView_(view)
    window.makeKeyAndOrderFront_(None)
    
    start = time.time()
    while time.time() - start < duration_ms / 1000.0:
        event = AppKit.NSApp.nextEventMatchingMask_untilDate_inMode_dequeue_(
            AppKit.NSAnyEventMask,
            AppKit.NSDate.dateWithTimeIntervalSinceNow_(0.05),
            AppKit.NSDefaultRunLoopMode,
            True
        )
        if event:
            AppKit.NSApp.sendEvent_(event)
    
    window.close()

if __name__ == "__main__":
    x = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    y = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    r = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    d = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
    app = AppKit.NSApplication.sharedApplication()
    draw_red_circle(x, y, r, d)
