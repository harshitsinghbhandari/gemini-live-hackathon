import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
USER_ID = os.environ.get("USER_ID", "harshitbhandari0318")

# Model Names
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_LIVE_MODEL = "gemini-2.5-flash-native-audio-latest"

# Audio Config
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# Timeouts & Intervals
SCREENSHOT_INTERVAL = 3
TOUCH_ID_TIMEOUT = 30
YELLOW_CONFIRM_TIMEOUT = 15

def setup_logging():
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    formatter = logging.Formatter(log_format)

    # Root logger
    logger = logging.getLogger("guardian")
    logger.setLevel(logging.DEBUG)

    # Avoid adding multiple handlers if setup_logging is called multiple times
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        # Rotating File Handler
        file_handler = RotatingFileHandler("guardian.log", maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    # Audit JSONL Logger
    audit_logger = logging.getLogger("guardian_audit")
    audit_logger.propagate = False
    audit_logger.setLevel(logging.INFO)

    if not audit_logger.handlers:
        audit_handler = RotatingFileHandler("guardian_audit.jsonl", maxBytes=10*1024*1024, backupCount=5)
        audit_handler.setFormatter(logging.Formatter("%(message)s"))
        audit_logger.addHandler(audit_handler)

    return logger
