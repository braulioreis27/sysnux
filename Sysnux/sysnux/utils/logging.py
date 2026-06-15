import os
import sys
from datetime import datetime

LOG_FILE = None


def setup_logging():
    global LOG_FILE
    log_dir = "/var/log"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_FILE = f"{log_dir}/sysnux_{timestamp}.log"
    return LOG_FILE


def log_message(level, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{timestamp}] [{level}] {message}"
    print(formatted, file=sys.stderr)
    if LOG_FILE:
        try:
            with open(LOG_FILE, "a") as f:
                f.write(formatted + "\n")
        except PermissionError:
            pass
    return formatted
