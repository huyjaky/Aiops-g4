"""Structured JSON logger for the closed-loop orchestrator."""

import os
import json
from datetime import datetime, timezone


class JsonLogger:
    """Emit structured JSON log records to stdout and to an audit log file."""

    def __init__(self, name: str):
        self._name = name

    def _emit(self, level: str, event_type: str, **kwargs):
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "level": level,
            "event_type": event_type,
            **kwargs,
        }
        log_line = json.dumps(record)
        print(log_line, flush=True)

        audit_log_path = os.environ.get("AUDIT_LOG_PATH", "audit_log.jsonl")
        if audit_log_path:
            try:
                parent_dir = os.path.dirname(os.path.abspath(audit_log_path))
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                with open(audit_log_path, "a") as f:
                    f.write(log_line + "\n")
            except Exception:
                pass

    def info(self, event_type: str, **kwargs):
        self._emit("INFO", event_type, **kwargs)

    def warning(self, event_type: str, **kwargs):
        self._emit("WARNING", event_type, **kwargs)

    def error(self, event_type: str, **kwargs):
        self._emit("ERROR", event_type, **kwargs)
