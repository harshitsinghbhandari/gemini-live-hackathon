"""
aegis_menubar.py — Mac menu bar entry point for Aegis.

Icons:
  ◈  idle      — session not running
  ◉  listening — connected, ready for voice input
  ◌  executing — tool call in progress
  ⊠  auth      — Touch ID / biometric prompt active
  ⊗  error     — session crashed
"""

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

    ICON_IDLE    = "◈"
    ICON_LISTEN  = "◉"
    ICON_EXECUTE = "◌"
    ICON_AUTH    = "⊠"
    ICON_ERROR   = "⊗"

    def __init__(self):
        super().__init__(self.ICON_IDLE, quit_button=None)
        self.menu = [
            rumps.MenuItem("Start Session", callback=self.toggle_session),
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
            None,  # separator
            rumps.MenuItem("Quit Aegis", callback=self.quit_app),
        ]
        self._running = False
        self._session_thread: threading.Thread | None = None
        self._session_loop: asyncio.AbstractEventLoop | None = None
        self._timeout_timer: threading.Timer | None = None

        # Attempt to register Cmd+Shift+A global hotkey via CGEventTap
        self._register_hotkey()

    # ─────────────────────────────────────────────
    #  Hotkey
    # ─────────────────────────────────────────────
    def _register_hotkey(self):
        """Register Cmd+Shift+A as a system-wide hotkey using CGEventTap."""
        try:
            from Quartz import (
                CGEventTapCreate, CGEventTapEnable,
                kCGSessionEventTap, kCGHeadInsertEventTap,
                kCGEventKeyDown, CGEventGetFlags, CGEventGetIntegerValueField,
                kCGKeyboardEventKeycode,
            )
            import CoreFoundation

            def _callback(proxy, type_, event, refcon):
                try:
                    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                    flags = CGEventGetFlags(event)
                    # Cmd = 0x100000 (NX_COMMANDMASK), Shift = 0x20000 (NX_SHIFTMASK)
                    CMD_SHIFT = 0x100000 | 0x20000
                    if keycode == 0 and (flags & CMD_SHIFT) == CMD_SHIFT:  # 'a' = keycode 0
                        self.toggle_session()
                except Exception:
                    pass
                return event

            tap = CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                0,
                1 << kCGEventKeyDown,
                _callback,
                None,
            )
            if tap:
                source = CoreFoundation.CFMachPortCreateRunLoopSource(None, tap, 0)
                CoreFoundation.CFRunLoopAddSource(
                    CoreFoundation.CFRunLoopGetMain(),
                    source,
                    CoreFoundation.kCFRunLoopCommonModes,
                )
                CGEventTapEnable(tap, True)
                logger.info("⌨️  Global hotkey Cmd+Shift+A registered")
            else:
                logger.warning("CGEventTap returned None — hotkey not registered (grant Accessibility permission)")
        except Exception as e:
            logger.warning(f"Global hotkey unavailable: {e}")

    # ─────────────────────────────────────────────
    #  Session lifecycle
    # ─────────────────────────────────────────────
    def toggle_session(self, _=None):
        if self._running:
            self._stop_session(reason="manual")
        else:
            self._start_session()

    def _start_session(self):
        self._running = True
        self._set_icon(self.ICON_LISTEN)
        self.menu["Start Session"].title = "Stop Session"

        # 60 second auto-stop timer
        self._timeout_timer = threading.Timer(60.0, self._auto_stop)
        self._timeout_timer.daemon = True
        self._timeout_timer.start()

        self._session_thread = threading.Thread(
            target=self._run_session_thread, daemon=True
        )
        self._session_thread.start()

        rumps.notification("Aegis", "", "Aegis is listening 🎙️")
        logger.info("🟢 Menu bar session started")

    def _run_session_thread(self):
        """Runs the async voice session in its own event loop on a background thread."""
        self._session_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._session_loop)
        try:
            self._session_loop.run_until_complete(
                run_aegis(status_callback=self._on_status_change)
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Session error: {e}")
            rumps.notification("Aegis", "Session Error", str(e)[:200])
            self._set_icon(self.ICON_ERROR)
        finally:
            self._session_loop.close()
            self._session_loop = None
            # Reset UI on the main thread
            self._running = False
            self._set_icon(self.ICON_IDLE)
            self.menu["Start Session"].title = "Start Session"

    def _stop_session(self, reason: str = "manual"):
        """Signal the background event loop to stop, cancel the timer."""
        if self._timeout_timer:
            self._timeout_timer.cancel()
            self._timeout_timer = None

        loop = self._session_loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)

        self._running = False
        self._set_icon(self.ICON_IDLE)
        self.menu["Start Session"].title = "Start Session"

        if reason == "timeout":
            rumps.notification("Aegis", "Session Ended", "60 second session limit reached.")
        elif reason == "manual":
            rumps.notification("Aegis", "Session Ended", "Session stopped.")

    def _auto_stop(self):
        """Called by the timeout timer (on its own thread)."""
        if self._running:
            logger.info("⏱️  Auto-stopping after 60 s")
            self._stop_session(reason="timeout")

    # ─────────────────────────────────────────────
    #  Status callback (called from background thread)
    # ─────────────────────────────────────────────
    def _on_status_change(self, status: str):
        icons = {
            "listening": self.ICON_LISTEN,
            "executing": self.ICON_EXECUTE,
            "auth":      self.ICON_AUTH,
            "error":     self.ICON_ERROR,
            "idle":      self.ICON_IDLE,
        }
        icon = icons.get(status, self.ICON_IDLE)
        self._set_icon(icon)

    # ─────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────
    def _set_icon(self, icon: str):
        """Thread-safe title update via rumps property setter."""
        rumps.App.title.fset(self, icon)

    # ─────────────────────────────────────────────
    #  Menu actions
    # ─────────────────────────────────────────────
    def open_dashboard(self, _):
        webbrowser.open(DASHBOARD_URL)

    def quit_app(self, _):
        self._stop_session(reason="quit")
        rumps.quit_application()


if __name__ == "__main__":
    AegisMenuBar().run()
