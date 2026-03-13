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
        self._agent = None
        self._running = False

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

        # Run voice session in background thread
        self._session_thread = threading.Thread(
            target=self._run_session,
            daemon=True
        )
        self._session_thread.start()

    def _on_agent_ready(self, agent):
        self._agent = agent

    def _run_session(self):
        """Runs async voice session in background thread"""
        self._session_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._session_loop)
        try:
            self._session_loop.run_until_complete(
                run_aegis(
                    status_callback=self.on_status_change,
                    on_agent_ready=self._on_agent_ready
                )
            )
        except Exception as e:
            logger.error(f"Session error: {e}")
            rumps.notification("Aegis", "Session Error", str(e))
            self.set_status(self.ICON_ERROR)
        finally:
            self._running = False
            self.set_status(self.ICON_IDLE)
            self.menu["Start Session"].title = "Start Session"

    def stop_session(self, _=None, reason="manual"):
        """Manually stop session"""
        if self._agent:
            logger.info("Requesting graceful stop of agent...")
            self._agent.request_stop()
        elif self._session_loop:
            logger.warning("Agent not ready, forcing loop stop.")
            self._session_loop.call_soon_threadsafe(
                self._session_loop.stop
            )

        self._running = False
        self.set_status(self.ICON_IDLE)
        self.menu["Start Session"].title = "Start Session"

        if reason == "manual":
            rumps.notification("Aegis", "Session Ended", "Session ended")

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
            icon = self.ICON_AUTH
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
