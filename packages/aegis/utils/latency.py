import time
import logging
from pathlib import Path

# Setup a dedicated logger for latency
latency_logger = logging.getLogger("aegis.latency")
latency_logger.propagate = False
latency_logger.setLevel(logging.INFO)

# Global tracker for last checkpoint time per component to calculate relative delta
_last_times = {}

LOG_FILE = Path("aegis.latency.log")

if not latency_logger.handlers:
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler(LOG_FILE, maxBytes=50*1024*1024, backupCount=2)
    handler.setFormatter(logging.Formatter("%(message)s"))
    latency_logger.addHandler(handler)

def checkpoint(component: str, tag: str):
    """
    Logs a latency checkpoint in the format: [component][tag] +delta_ms
    """
    now = time.time_ns() // 1_000_000  # ms
    
    last_time = _last_times.get(component)
    if last_time is None:
        delta = 0
    else:
        delta = now - last_time
        
    _last_times[component] = now
    
    msg = f"[{component}][{tag}] +{delta}ms"
    latency_logger.info(msg)
