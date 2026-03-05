import rumps
import asyncio
import threading
import webbrowser
import logging
from aegis.voice import run_aegis
from aegis.config import DASHBOARD_URL, setup_logging

setup_logging()
logger = logging.getLogger("aegis.menubar")

class AegisMenuBar(rumps.App):

    ICON_IDLE     = "◈"
    ICON_LISTEN   = "◉"
    ICON_EXECUTE  = "◌"
    ICON_AUTH     = "⊠"
    ICON_ERROR    = "⊗"

    def __init__(self):
        super().__init__(self.ICON_IDLE, quit_button=None)
        self.menu = [
            rumps.MenuItem("Start Session", callback=self.start_session),
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
            None,  # separator
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        self._session_thread = None
        self._session_loop = None
        self._running = False
        self._timeout_timer = None

        # Register global hotkey Cmd+Shift+A
        self._register_hotkey()

    def _register_hotkey(self):
        """Register Cmd+Shift+A as global hotkey using CGEventTap"""
        try:
            from Quartz import (
                CGEventTapCreate, kCGSessionEventTap,
                kCGHeadInsertEventTap, kCGEventKeyDown,
                CGEventGetFlags, CGEventGetIntegerValueField,
                kCGKeyboardEventKeycode, CGEventTapEnable
            )
            import CoreFoundation

            def hotkey_callback(proxy, type_, event, refcon):
                try:
                    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                    flags = CGEventGetFlags(event)
                    # Cmd = 0x100000, Shift = 0x20000
                    cmd_shift = 0x100000 | 0x20000
                    # keycode 0 = 'a'
                    if keycode == 0 and (flags & cmd_shift) == cmd_shift:
                        self.start_session()
                except Exception:
                    pass
                return event

            tap = CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                0,
                1 << kCGEventKeyDown,
                hotkey_callback,
                None
            )
            if tap:
                source = CoreFoundation.CFMachPortCreateRunLoopSource(None, tap, 0)
                CoreFoundation.CFRunLoopAddSource(
                    CoreFoundation.CFRunLoopGetMain(),
                    source,
                    CoreFoundation.kCFRunLoopCommonModes
                )
                CGEventTapEnable(tap, True)
                logger.info("⌨️ Global hotkey Cmd+Shift+A registered")
            else:
                logger.warning("CGEventTap failed (needs Accessibility permissions)")
        except Exception as e:
            logger.warning(f"Hotkey registration failed: {e}")

    def set_status(self, icon: str, menu_label: str = None):
        """Thread-safe icon + menu update"""
        rumps.App.title.fset(self, icon)
        if menu_label and "Start Session" in self.menu:
            self.menu["Start Session"].title = menu_label

    def start_session(self, _=None):
        """Start Aegis voice session"""
        if self._running:
            self.stop_session(reason="manual")
            return

        self._running = True
        self.set_status(self.ICON_LISTEN)
        self.menu["Start Session"].title = "Stop Session"

        rumps.notification("Aegis", "", "Aegis is listening 🎙️")

        # Start 60 second timeout timer
        self._timeout_timer = threading.Timer(60.0, self.auto_stop)
        self._timeout_timer.daemon = True
        self._timeout_timer.start()

        # Run voice session in background thread
        self._session_thread = threading.Thread(
            target=self._run_session,
            daemon=True
        )
        self._session_thread.start()

    def _run_session(self):
        """Runs async voice session in background thread"""
        self._session_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._session_loop)
        try:
            self._session_loop.run_until_complete(
                run_aegis(status_callback=self.on_status_change)
            )
        except Exception as e:
            logger.error(f"Session error: {e}")
            rumps.notification("Aegis", "Session Error", str(e))
            self.set_status(self.ICON_ERROR)
        finally:
            self._running = False
            self.set_status(self.ICON_IDLE)
            self.menu["Start Session"].title = "Start Session"
            if self._timeout_timer:
                self._timeout_timer.cancel()

    def stop_session(self, _=None, reason="manual"):
        """Manually stop session"""
        if self._timeout_timer:
            self._timeout_timer.cancel()
        if self._session_loop:
            self._session_loop.call_soon_threadsafe(
                self._session_loop.stop
            )
        self._running = False
        self.set_status(self.ICON_IDLE)
        self.menu["Start Session"].title = "Start Session"

        if reason == "manual":
            rumps.notification("Aegis", "Session Ended", "Session ended")

    def auto_stop(self):
        """Auto stop after 60 seconds of session"""
        if self._running:
            rumps.notification(
                "Aegis",
                "Session Ended",
                "60 second session limit reached."
            )
            self.stop_session(reason="timeout")

    def on_status_change(self, status: str):
        """Called by voice layer to update icon"""
        icons = {
            "listening":  self.ICON_LISTEN,
            "executing":  self.ICON_EXECUTE,
            "auth":       self.ICON_AUTH,
            "error":      self.ICON_ERROR,
            "idle":       self.ICON_IDLE,
            "blocked":    self.ICON_ERROR  # Showing error icon for blocked? Or ICON_AUTH?
                                           # The prompt says "RED action blocked: 'Action blocked — Touch ID failed'"
                                           # Let's handle notification here.
        }

        if status == "blocked":
            rumps.notification("Aegis", "Action Blocked", "Action blocked — Touch ID failed")
            icon = self.ICON_ERROR
        else:
            icon = icons.get(status, self.ICON_IDLE)

        # Thread safe UI update
        self.set_status(icon)

    def open_dashboard(self, _):
        webbrowser.open(DASHBOARD_URL)

    def quit_app(self, _):
        self.stop_session(reason="quit")
        rumps.quit_application()

if __name__ == "__main__":
    AegisMenuBar().run()
