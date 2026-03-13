import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
USER_ID = os.environ.get("USER_ID", "harshitbhandari0318")
AEGIS_PIN = os.environ.get("AEGIS_PIN", "")

# Model Names
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_PRO_MODEL = "gemini-3.1-flash-lite-preview" # Strategist model
GEMINI_LIVE_MODEL = "gemini-2.5-flash-native-audio-latest"
# GEMINI_LIVE_MODEL = 'gemini-2.0-flash-exp'

# Audio Config
VOICE_NAME = "Aoede"
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# Timeouts & Intervals
SCREENSHOT_INTERVAL = 3
SETTLING_DELAY = 0.2  # Seconds between multi-tool actions
TOUCH_ID_TIMEOUT = 30
YELLOW_CONFIRM_TIMEOUT = 15

# Foveated Vision Config
VISION_PADDING = 50  # Pixels to expand around active window crop
VISION_FALLBACK_TO_FULLSCREEN = True  # Fall back to full screen if window detection fails

# Backend Config
BACKEND_URL = os.environ.get("BACKEND_URL", "https://apiaegis.projectalpha.in")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "https://aegisdashboard.projectalpha.in")
DEVICE_ID = os.environ.get("DEVICE_ID", "harshit-macbook")

class LevelFilter(logging.Filter):
    """Filters logs to be exactly of a certain level (exclusive)."""
    def __init__(self, level):
        self.level = level
    def filter(self, record):
        return record.levelno == self.level

def setup_logging():
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    formatter = logging.Formatter(log_format)

    # Root logger
    logger = logging.getLogger("aegis")
    logger.setLevel(logging.DEBUG)

    # Avoid adding multiple handlers if setup_logging is called multiple times
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        # 1. Debug File (Exclusive)
        debug_handler = RotatingFileHandler("aegis.debug.log", maxBytes=10*1024*1024, backupCount=5)
        debug_handler.setFormatter(formatter)
        debug_handler.addFilter(LevelFilter(logging.DEBUG))
        logger.addHandler(debug_handler)

        # 2. Info File (Exclusive)
        info_handler = RotatingFileHandler("aegis.info.log", maxBytes=10*1024*1024, backupCount=5)
        info_handler.setFormatter(formatter)
        info_handler.addFilter(LevelFilter(logging.INFO))
        logger.addHandler(info_handler)

        # 3. Warning File (Exclusive)
        warn_handler = RotatingFileHandler("aegis.warning.log", maxBytes=10*1024*1024, backupCount=5)
        warn_handler.setFormatter(formatter)
        warn_handler.addFilter(LevelFilter(logging.WARNING))
        logger.addHandler(warn_handler)

        # 4. Error/Critical File (Inclusive)
        error_handler = RotatingFileHandler("aegis.error.log", maxBytes=10*1024*1024, backupCount=5)
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)

    # Audit JSONL Logger
    audit_logger = logging.getLogger("aegis_audit")
    audit_logger.propagate = False
    audit_logger.setLevel(logging.INFO)

    if not audit_logger.handlers:
        audit_handler = RotatingFileHandler("aegis_audit.jsonl", maxBytes=10*1024*1024, backupCount=5)
        audit_handler.setFormatter(logging.Formatter("%(message)s"))
        audit_logger.addHandler(audit_handler)

    # Screen Logger
    screen_logger = logging.getLogger("aegis.screen")
    screen_logger.setLevel(logging.DEBUG)
    screen_logger.propagate = False # Keep screen logs exclusive to their own file
    
    if not screen_logger.handlers:
        screen_handler = RotatingFileHandler("aegis.screen.log", maxBytes=10*1024*1024, backupCount=5)
        screen_handler.setFormatter(formatter)
        screen_handler.setLevel(logging.DEBUG)
        screen_logger.addHandler(screen_handler)

    return logger
