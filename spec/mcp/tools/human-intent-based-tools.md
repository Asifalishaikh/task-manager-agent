# Intent-Based Tools — Task Management MCP Server

> **Status:** Draft  
> **Date:** 2026-05-08  
> **Design principle:** Tools map to human intents, not CRUD operations.

---

## Tool Overview

| # | Tool | Human Intent | Analogous CRUD |
|---|------|-------------|----------------|
| 1 | `capture_task` | "I need to remember something" | CREATE |
| 2 | `review_task` | "Show me what I have" | READ (list + search) |
| 3 | `modify_task` | "Change something about a task" | UPDATE |
| 4 | `resolve_task` | "This is done" | UPDATE (status→done) |
| 5 | `remove_task` | "Get rid of this" | DELETE |

---

## 1. `capture_task` — "I need to remember something"

**Purpose:** Store a task from natural language. The agent extracts what matters.

**What an agent might say to invoke this:**
> *"Remind me to review the PR at 3pm"*  
> *"Add a high priority task to fix the login bug"*  
> *"Note that we need to upgrade the database next quarter"*

```python
@mcp.tool(
    name="capture_task",
    annotations={
        "title": "Capture a Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
```

**Input:**
```python
class CaptureTaskInput(BaseModel):
    title: str = Field(..., description="Task title (concise, what needs to be done)", min_length=1, max_length=200)
    description: str = Field(default="", description="Details, context, notes about the task", max_length=2000)
    priority: str = Field(default="medium", description="Priority level: low, medium, high, critical")
    assignee: str = Field(default="", description="Person responsible (empty if unassigned)")
    tags: list[str] = Field(default_factory=list, description="Labels for categorization", max_length=10)
```

**Output:** Returns the created task with generated ID and timestamps.

---

## 2. `review_task` — "Show me what I have"

**Purpose:** Look up tasks — list, filter, search, or get details. Combines listing + search into one intent.

**What an agent might say:**
> *"What's on my plate today?"*  
> *"Find the task about deploying to Kubernetes"*  
> *"Show all high priority tasks assigned to Sara"*  
> *"What tasks are overdue?"*

```python
@mcp.tool(
    name="review_task",
    annotations={
        "title": "Review Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
```

**Input:**
```python
class ReviewTaskInput(BaseModel):
    query: str = Field(default="", description="Natural language search (e.g., 'deploy kubernetes', 'login bug')")
    status: str = Field(default="", description="Filter by status: not_started, in_progress, done, cancelled (empty = all)")
    priority: str = Field(default="", description="Filter by priority: low, medium, high, critical (empty = all)")
    assignee: str = Field(default="", description="Filter by assignee name (empty = all)")
    tag: str = Field(default="", description="Filter by tag (empty = all)")
    limit: int = Field(default=50, description="Maximum results", ge=1, le=200)
```

**Output:** Formatted list of matching tasks with status, priority, assignee, due info.

---

## 3. `modify_task` — "Change something about a task"

**Purpose:** Update any field(s) of an existing task. Partial update — only provided fields change.

**What an agent might say:**
> *"Change the title of the database task to 'Migrate to PostgreSQL'"*  
> *"Move the frontend work to high priority"*  
> *"Add 'urgent' and 'ui' tags to the login page task"*  
> *"Reassign the API design task to Muhammad"*

```python
@mcp.tool(
    name="modify_task",
    annotations={
        "title": "Modify a Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
```

**Input:**
```python
class ModifyTaskInput(BaseModel):
    task_id: str = Field(..., description="ID of the task to modify")
    title: str = Field(default=None, description="New title", min_length=1, max_length=200)
    description: str = Field(default=None, description="New description", max_length=2000)
    priority: str = Field(default=None, description="New priority: low, medium, high, critical")
    assignee: str = Field(default=None, description="New assignee (empty string to unassign)")
    tags: list[str] = Field(default=None, description="Replace tags with this list")
    add_tags: list[str] = Field(default_factory=list, description="Tags to append", max_length=5)
    remove_tags: list[str] = Field(default_factory=list, description="Tags to remove", max_length=5)
```

**Note:** `tags`, `add_tags`, and `remove_tags` give fine-grained tag control without requiring the agent to know the full tag list.

---

## 4. `resolve_task` — "This is done"

**Purpose:** Mark a task as completed/resolved. Separate from modify because this is a distinct human action — "I'm done with this."

**What an agent might say:**
> *"Mark the API design task as done"*  
> *"The login bug is resolved"*  
> *"I finished reviewing the PR"*

```python
@mcp.tool(
    name="resolve_task",
    annotations={
        "title": "Resolve a Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
```

**Input:**
```python
class ResolveTaskInput(BaseModel):
    task_id: str = Field(..., description="ID of the task to mark as resolved/done")
    resolution_note: str = Field(default="", description="Optional note about how it was resolved", max_length=500)
```

**Output:** Confirmation with the resolved task and timestamp.

**Behavior:**
- Sets status to `done`
- Records completion timestamp
- Preserves all other fields

---

## 5. `remove_task` — "Get rid of this"

**Purpose:** Delete a task entirely. Distinct from resolve — this is discarding, not completing.

**What an agent might say:**
> *"Delete the duplicate task about database migration"*  
> *"Remove the 'upgrade dependencies' task, it's no longer needed"*  
> *"Cancel the design review task"*

```python
@mcp.tool(
    name="remove_task",
    annotations={
        "title": "Remove a Task",
        "readOnlyHint": False,
        "destructiveHint": True,   # Destructive — cannot be undone
        "idempotentHint": False,
        "openWorldHint": False
    }
)
```

**Input:**
```python
class RemoveTaskInput(BaseModel):
    task_id: str = Field(..., description="ID of the task to permanently remove")
    reason: str = Field(default="", description="Reason for removal (for audit trail)", max_length=300)
```

**Output:** Confirmation of removal.

---

## Task Model (Data Layer)

All tools operate on this unified model:

```python
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
    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.NOT_STARTED
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee: str = ""
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
```

---

## Tool Annotations Summary

> **Note:** User concept, auth, DB, and K8s are future phases. See [`spec/mcp/roadmap/evolution-phases.md`](../roadmap/evolution-phases.md).



| Tool | readOnlyHint | destructiveHint | idempotentHint | openWorldHint |
|------|:---:|:---:|:---:|:---:|
| `capture_task` | ❌ | ❌ | ❌ | ❌ |
| `review_task` | ✅ | ❌ | ✅ | ❌ |
| `modify_task` | ❌ | ❌ | ✅ | ❌ |
| `resolve_task` | ❌ | ❌ | ✅ | ❌ |
| `remove_task` | ❌ | ✅ | ❌ | ❌ |
