"""
request log: one json line per request in logs/requests.jsonl.
"""

import json
import os
from datetime import datetime, timezone


LOG_DIR = "logs"
LOG_PATH = os.path.join(LOG_DIR, "requests.jsonl")


def log_request(message, result, latency_seconds, model, error=None):
    os.makedirs(LOG_DIR, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "latency_seconds": round(latency_seconds, 3),
        "input": message,
        "output": result,
        "error": error,
    }
    with open(LOG_PATH, "a") as file:
        file.write(json.dumps(entry) + "\n")
