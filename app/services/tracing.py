import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRACE_DIR = Path("data/traces")


class AgentTrace:
    def __init__(self, user_message: str) -> None:
        self.trace_id = uuid.uuid4().hex
        self.user_message = user_message
        self.started_at = time.perf_counter()
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        self.path = TRACE_DIR / f"{self.trace_id}.jsonl"
        self.event(
            "trace_started",
            {
                "user_message": user_message,
            },
        )

    def event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        record = {
            "trace_id": self.trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": round((time.perf_counter() - self.started_at) * 1000, 2),
            "event": event_type,
            "payload": payload or {},
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def finish(self, final_answer: str | None = None) -> None:
        self.event(
            "trace_finished",
            {
                "final_answer": final_answer,
            },
        )
