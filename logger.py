"""
logger.py - the Logging Layer.

Appends one JSON line per request to logs/requests.jsonl:
    time, input message, full output (or the error), latency in seconds, model name.

Covers PDF §6 "Logging of all requests and outputs" and §11 "log inputs, outputs, latency".
"""

import json
import os
from datetime import datetime, timezone


LOG_DIR = "logs"
LOG_PATH = os.path.join(LOG_DIR, "requests.jsonl")


def log_request(message, result, latency_seconds, model, error=None):
    """Append one request (successful or failed) to the log file."""
    os.makedirs(LOG_DIR, exist_ok=True)  # create logs/ the first time; do nothing if it exists

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "latency_seconds": round(latency_seconds, 3),
        "input": message,
        "output": result,
        "error": error,
    }
    with open(LOG_PATH, "a") as file:  # "a" = append: add to the end, never overwrite
        file.write(json.dumps(entry) + "\n")
