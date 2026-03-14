import logging
import os
import time
import threading
import atexit
import contextvars
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional

# --- Logging Setup ---
# Find project root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LOG_FILE = os.path.join(ROOT_DIR, "aegis.latency.log")
SUMMARY_FILE = os.path.join(ROOT_DIR, "aegis.latency.summary.log")

# Dedicated logger for real-time latency events
latency_logger = logging.getLogger("aegis_latency")
latency_logger.setLevel(logging.INFO)
latency_logger.propagate = False

# File handler with plain format
fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(logging.Formatter('%(message)s'))
latency_logger.addHandler(fh)

# Console handler with distinct marker
class ConsoleMarkerFormatter(logging.Formatter):
    def format(self, record):
        formatted = super().format(record)
        return f"⏱ {formatted}"

ch = logging.StreamHandler()
ch.setFormatter(ConsoleMarkerFormatter('%(message)s'))
latency_logger.addHandler(ch)

# --- State Management ---

# Context-local storage for traces
# None default to ensure we initialize a fresh dict per context
_state_var: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar('aegis_latency_state', default=None)

def _get_local_state() -> Dict[str, Any]:
    state = _state_var.get()
    if state is None:
        state = {}
        _state_var.set(state)
    return state

# --- API Functions ---

def checkpoint(category: str, label: str):
    """
    Records a timestamped event under a category.
    The delta is relative to the last checkpoint in the same category.
    """
    now = time.perf_counter()
    state = _get_local_state()

    if category not in state:
        state[category] = {
            "events": [],
            "last_time": now
        }
    
    cat_data = state[category]
    delta_ms = int((now - cat_data["last_time"]) * 1000)
    
    # Store event with raw timestamp and calculated delta
    cat_data["events"].append((label, now, delta_ms))
    cat_data["last_time"] = now

    # Real-time log
    latency_logger.info(f"[{category}][{label}] +{delta_ms}ms")

def flush_summary(session_name: str = "session"):
    """
    Compiles everything collected in the current context and writes a summary.
    Then resets the internal state.
    """
    state = _get_local_state()
    if not state:
        return

    # Total timeline across all categories
    all_events = []
    for cat in state.values():
        all_events.extend(cat["events"])
    
    if not all_events:
        return

    # Sort events by global timestamp to find first/last
    all_events.sort(key=lambda x: x[1])
    start_ts = all_events[0][1]
    end_ts = all_events[-1][1]
    wall_duration_s = end_ts - start_ts

    def format_relative(ts):
        diff = ts - start_ts
        mins, secs = divmod(diff, 60)
        hrs, mins = divmod(mins, 60)
        ms = int((secs - int(secs)) * 1000)
        return f"{int(hrs):02d}:{int(mins):02d}:{int(secs):02d}.{ms:03d}"

    summary = []
    summary.append("════════════════════════════════════════")
    summary.append(f"LATENCY SUMMARY — {session_name}")
    summary.append("════════════════════════════════════════")
    summary.append("")

    for cat_name in sorted(state.keys()):
        summary.append(f"[{cat_name}]")
        cat_data = state[cat_name]
        
        # Aggregate labels while preserving encounter order
        label_map = defaultdict(list)
        ordered_labels = []
        for label, _, delta in cat_data["events"]:
            if label not in label_map:
                ordered_labels.append(label)
            label_map[label].append(delta)
        
        cat_total_ms = 0
        for label in ordered_labels:
            deltas = label_map[label]
            count = len(deltas)
            total = sum(deltas)
            cat_total_ms += total
            
            if count == 1:
                summary.append(f"  {label:<24} {total}ms")
            else:
                avg = int(total / count)
                imin = min(deltas)
                imax = max(deltas)
                summary.append(f"  {label:<10} × {count:<8} avg {avg}ms  min {imin}ms  max {imax}ms  total {total}ms")
        
        summary.append("  " + "─" * 29)
        summary.append(f"  total                   {cat_total_ms}ms")
        summary.append("")

    summary.append("────────────────────────────────────────")
    summary.append(f"FIRST CHECKPOINT          {format_relative(start_ts)}")
    summary.append(f"LAST CHECKPOINT           {format_relative(end_ts)}")
    
    # Wall time format
    wall_mins, wall_secs = divmod(int(wall_duration_s), 60)
    if wall_mins > 0:
        wall_time_str = f"{wall_mins}m {wall_secs}s"
    else:
        wall_time_str = f"{wall_secs}s"
    summary.append(f"WALL TIME                 {wall_time_str}")
    summary.append("════════════════════════════════════════\n")

    # Write summary
    try:
        with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(summary) + "\n")
    except Exception as e:
        latency_logger.error(f"Error writing latency summary: {e}")

    # Reset state for current context
    _state_var.set({})

# --- Auto-dump on exit ---

def _atexit_handler():
    # Only if data exists in main thread context
    state = _state_var.get()
    if state:
        flush_summary("auto_exit")

atexit.register(_atexit_handler)
