import copy
import threading
from typing import Any


class JobRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}

    def create(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                raise ValueError(f"Job '{job_id}' already exists")
            self._jobs[job_id] = {"status": "running"}

    def update(self, job_id: str, patch: dict[str, Any]) -> None:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job '{job_id}' not found")
            self._jobs[job_id] = {**self._jobs[job_id], **patch}

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            return copy.deepcopy(self._jobs[job_id]) if job_id in self._jobs else None
