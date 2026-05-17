from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: str = Field(..., description="Unique task identifier (UUID)")
    title: str = Field(..., description="Task title (concise, what needs to be done)", min_length=1, max_length=200)
    description: str = Field(default="", description="Details, context, notes about the task", max_length=2000)
    status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the task")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Priority level")
    assignee: str = Field(default="", description="Person responsible (empty if unassigned)")
    tags: list[str] = Field(default_factory=list, description="Labels for categorization", max_length=10)
    created_at: datetime = Field(..., description="When the task was created")
    updated_at: datetime = Field(..., description="When the task was last modified")
    resolved_at: datetime | None = Field(default=None, description="When the task was marked done")


class CaptureTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(..., description="Task title (concise, what needs to be done)", min_length=1, max_length=200)
    description: str = Field(default="", description="Details, context, notes about the task", max_length=2000)
    priority: str = Field(default="medium", description="Priority level: low, medium, high, critical")
    assignee: str = Field(default="", description="Person responsible (empty if unassigned)")
    tags: list[str] = Field(default_factory=list, description="Labels for categorization", max_length=10)


class ReviewTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(default="", description="Natural language search (e.g., 'deploy kubernetes', 'login bug')")
    status: str = Field(default="", description="Filter by status: not_started, in_progress, done, cancelled (empty = all)")
    priority: str = Field(default="", description="Filter by priority: low, medium, high, critical (empty = all)")
    assignee: str = Field(default="", description="Filter by assignee name (empty = all)")
    tag: str = Field(default="", description="Filter by tag (empty = all)")
    limit: int = Field(default=50, description="Maximum results to return", ge=1, le=200)


class ModifyTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    task_id: str = Field(..., description="ID of the task to modify")
    title: Optional[str] = Field(default=None, description="New title", min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, description="New description", max_length=2000)
    priority: Optional[str] = Field(default=None, description="New priority: low, medium, high, critical")
    assignee: Optional[str] = Field(default=None, description="New assignee (empty string to unassign)")
    tags: Optional[list[str]] = Field(default=None, description="Replace tags with this list", max_length=10)
    add_tags: list[str] = Field(default_factory=list, description="Tags to append", max_length=5)
    remove_tags: list[str] = Field(default_factory=list, description="Tags to remove", max_length=5)


class ResolveTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    task_id: str = Field(..., description="ID of the task to mark as resolved/done")
    resolution_note: str = Field(default="", description="Optional note about how it was resolved", max_length=500)


class RemoveTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    task_id: str = Field(..., description="ID of the task to permanently remove")
    reason: str = Field(default="", description="Reason for removal (for audit trail)", max_length=300)
