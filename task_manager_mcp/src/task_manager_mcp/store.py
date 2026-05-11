from __future__ import annotations

import uuid
from datetime import datetime
from threading import Lock
from typing import Optional

from .models import Task, TaskPriority, TaskStatus


class InMemoryTaskStore:
    """Thread-safe in-memory task storage.

    All methods acquire/release self._lock for concurrent access
    from multiple agents calling tools simultaneously.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = Lock()

    def create(self, data: dict) -> Task:
        now = datetime.now()
        task = Task(
            id=uuid.uuid4().hex,
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=TaskStatus.NOT_STARTED,
            priority=TaskPriority(data.get("priority", "medium")),
            assignee=data.get("assignee", ""),
            tags=data.get("tags", []),
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def list(
        self,
        query: str = "",
        status: str = "",
        priority: str = "",
        assignee: str = "",
        tag: str = "",
        limit: int = 50,
    ) -> list[Task]:
        with self._lock:
            results = list(self._tasks.values())

        # Full-text search across title and description
        if query:
            q = query.lower()
            results = [
                t
                for t in results
                if q in t.title.lower() or q in t.description.lower()
            ]

        # Exact match filters
        if status:
            results = [t for t in results if t.status.value == status]
        if priority:
            results = [t for t in results if t.priority.value == priority]
        if assignee:
            results = [t for t in results if t.assignee == assignee]
        if tag:
            results = [t for t in results if tag in t.tags]

        # Sort by created_at descending (newest first)
        results.sort(key=lambda t: t.created_at, reverse=True)

        return results[:limit]

    def update(self, task_id: str, data: dict) -> Task:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Task not found: {task_id}")

            # Build updated fields (partial update)
            updates: dict = {}

            if "title" in data and data["title"] is not None:
                updates["title"] = data["title"]
            if "description" in data and data["description"] is not None:
                updates["description"] = data["description"]
            if "priority" in data and data["priority"] is not None:
                updates["priority"] = TaskPriority(data["priority"])
            if "assignee" in data and data["assignee"] is not None:
                updates["assignee"] = data["assignee"]

            # Tag merging logic
            if "tags" in data and data["tags"] is not None:
                updates["tags"] = data["tags"]
            else:
                current_tags = list(task.tags)
                add_tags = data.get("add_tags", [])
                remove_tags = data.get("remove_tags", [])
                for t in remove_tags:
                    if t in current_tags:
                        current_tags.remove(t)
                for t in add_tags:
                    if t not in current_tags:
                        current_tags.append(t)
                updates["tags"] = current_tags

            updates["updated_at"] = datetime.now()

            updated = task.model_copy(update=updates)
            self._tasks[task_id] = updated
            return updated

    def resolve(self, task_id: str, note: str = "") -> Task:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Task not found: {task_id}")

            now = datetime.now()
            description = task.description
            if note:
                description = (description + f"\n\n[Resolution: {note}]").strip()

            updated = task.model_copy(
                update={
                    "status": TaskStatus.DONE,
                    "resolved_at": now,
                    "updated_at": now,
                    "description": description,
                }
            )
            self._tasks[task_id] = updated
            return updated

    def delete(self, task_id: str) -> None:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task not found: {task_id}")
            del self._tasks[task_id]
