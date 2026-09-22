"""
DocStudio Browser Visual Provider — Generation Queue.
Prevents browser crashes and provider throttling by managing task concurrency.
Tracks pending, running, completed, failed, and retrying states.
"""

from __future__ import annotations
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class QueueTask:
    task_id: str
    shot_id: str
    request_payload: Dict[str, Any]
    state: TaskState = TaskState.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "shot_id": self.shot_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_path": self.result_path,
            "error_message": self.error_message,
            "attempts": self.attempts,
        }


class BrowserGenerationQueue:
    """
    Thread-safe concurrency queue for browser-based creative generation.
    """

    def __init__(self, max_concurrency: int = 1):
        self.max_concurrency = max(1, max_concurrency)
        self._lock = threading.Lock()
        self._tasks: Dict[str, QueueTask] = {}

    def enqueue(self, shot_id: str, request_payload: Dict[str, Any]) -> QueueTask:
        with self._lock:
            task_id = f"task_{shot_id}_{int(time.time() * 1000)}"
            task = QueueTask(
                task_id=task_id,
                shot_id=shot_id,
                request_payload=request_payload,
            )
            self._tasks[task_id] = task
            return task

    def get_task(self, task_id: str) -> Optional[QueueTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def acquire_next_task(self) -> Optional[QueueTask]:
        """Returns the next pending task if running count is under max_concurrency."""
        with self._lock:
            running_count = sum(1 for t in self._tasks.values() if t.state == TaskState.RUNNING)
            if running_count >= self.max_concurrency:
                return None

            for task in self._tasks.values():
                if task.state in [TaskState.PENDING, TaskState.RETRYING]:
                    task.state = TaskState.RUNNING
                    task.started_at = time.time()
                    task.attempts += 1
                    return task
            return None

    def mark_completed(self, task_id: str, result_path: str) -> None:
        with self._lock:
            if task_id in self._tasks:
                t = self._tasks[task_id]
                t.state = TaskState.COMPLETED
                t.completed_at = time.time()
                t.result_path = result_path

    def mark_failed(self, task_id: str, error: str) -> None:
        with self._lock:
            if task_id in self._tasks:
                t = self._tasks[task_id]
                if t.attempts < t.max_attempts:
                    t.state = TaskState.RETRYING
                    t.error_message = f"Attempt {t.attempts} failed: {error}"
                else:
                    t.state = TaskState.FAILED
                    t.completed_at = time.time()
                    t.error_message = error

    def get_summary(self) -> Dict[str, int]:
        with self._lock:
            return {
                "total": len(self._tasks),
                "pending": sum(1 for t in self._tasks.values() if t.state == TaskState.PENDING),
                "running": sum(1 for t in self._tasks.values() if t.state == TaskState.RUNNING),
                "completed": sum(1 for t in self._tasks.values() if t.state == TaskState.COMPLETED),
                "failed": sum(1 for t in self._tasks.values() if t.state == TaskState.FAILED),
            }
