# Implementation Plan - Task Manager MCP Server

> **Status:** Plan  
> **Date:** 2026-05-08  
> **Package manager:** `uv`  
> **Framework:** FastMCP (Python)  
> **Transport:** Streamable HTTP  

---

## Step 1 - Project Setup

Create the MCP server package alongside the existing project.

```bash
# Create package directory
mkdir -p task_manager_mcp/src/task_manager_mcp/tools

# Init pyproject.toml with uv
cd task_manager_mcp
uv init --app --python 3.12
```

**Project structure:**

```
task_manager_mcp/
  src/
    task_manager_mcp/
      __init__.py
      __main__.py          # Entry point: python -m task_manager_mcp
      server.py             # FastMCP initialization & transport
      models.py             # Task, TaskStatus, TaskPriority
      store.py              # InMemoryTaskStore
      tools/
        __init__.py
        capture.py          # capture_task
        review.py           # review_task
        modify.py           # modify_task
        resolve.py          # resolve_task
        remove.py           # remove_task
  pyproject.toml
```

---

## Step 2 - Dependencies

```bash
cd task_manager_mcp
uv add "mcp[cli]"
```

This installs:
- `mcp` (FastMCP framework with CLI support)
- `httpx` (async HTTP client, comes with mcp)
- `pydantic` (validation, comes with mcp)

No other dependencies needed for Phase 1.

---

## Step 3 - Data Model (`src/task_manager_mcp/models.py`)

Define:
- `TaskStatus` enum: `not_started`, `in_progress`, `done`, `cancelled`
- `TaskPriority` enum: `low`, `medium`, `high`, `critical`
- `Task` Pydantic model: id, title, description, status, priority, assignee, tags, created_at, updated_at, resolved_at
- Input models for each tool (CaptureTaskInput, ReviewTaskInput, ModifyTaskInput, ResolveTaskInput, RemoveTaskInput)

All fields with `description=` so FastMCP auto-generates tool schemas.

---

## Step 4 - Storage (`src/task_manager_mcp/store.py`)

Implement `InMemoryTaskStore` class with methods:

| Method | Maps to tool | Behavior |
|--------|-------------|----------|
| `create(data)` | capture_task | Generate UUID id, set timestamps, store in dict |
| `list(filters)` | review_task | Filter by status/priority/assignee/tag, support text search, sort by created_at desc |
| `get(task_id)` | review_task | Single task lookup |
| `update(task_id, data)` | modify_task | Partial update, set updated_at |
| `resolve(task_id, note)` | resolve_task | Set status=done, set resolved_at |
| `delete(task_id)` | remove_task | Remove from dict |

Use `threading.Lock` for thread safety (multiple agents calling concurrently).

---

## Step 5 - Tools (`src/task_manager_mcp/tools/`)

Each tool file registers one tool on the shared `mcp` instance:

### capture.py
```
@mcp.tool(name="capture_task", ...)
async def capture_task(input: CaptureTaskInput) -> str
  -> store.create(input)
  -> return formatted task with id
```

### review.py
```
@mcp.tool(name="review_task", ...)
async def review_task(input: ReviewTaskInput) -> str
  -> if input.query: full-text search across titles/descriptions
  -> else: filter by status/priority/assignee/tag
  -> return markdown formatted list or single task detail
```

### modify.py
```
@mcp.tool(name="modify_task", ...)
async def modify_task(input: ModifyTaskInput) -> str
  -> store.update(input.task_id, fields)
  -> handle add_tags / remove_tags merging
  -> return updated task
```

### resolve.py
```
@mcp.tool(name="resolve_task", ...)
async def resolve_task(input: ResolveTaskInput) -> str
  -> store.resolve(input.task_id, input.resolution_note)
  -> return resolved task with completion timestamp
```

### remove.py
```
@mcp.tool(name="remove_task", ...)
@mcp.tool annotation: destructiveHint=True
async def remove_task(input: RemoveTaskInput) -> str
  -> store.delete(input.task_id)
  -> return confirmation
```

---

## Step 6 - Server & Entry Point (`src/task_manager_mcp/server.py`)

```python
from mcp.server.fastmcp import FastMCP
from .store import InMemoryTaskStore

# Create shared instances
mcp = FastMCP("task_manager_mcp")
store = InMemoryTaskStore()

# Import tools (they register themselves via @mcp.tool decorator)
from .tools import capture, review, modify, resolve, remove
```

### `__main__.py`
```python
from .server import mcp

if __name__ == "__main__":
    mcp.run(transport="streamable_http", port=8000)
```

---

## Step 7 - Running the Server

```bash
# From task_manager_mcp/ directory:
uv run python -m task_manager_mcp

# Or with uv run directly:
uv run --package task_manager_mcp python -m task_manager_mcp

# Server starts at: http://localhost:8000/mcp
```

---

## Step 8 - Testing with MCP Inspector

```bash
# Using the inspector CLI (from any directory):
npx @modelcontextprotocol/inspector

# Point it to: http://localhost:8000/mcp
# This opens a web UI to test tool calls interactively
```

---

## Step 9 - Connecting Claude Code

Create `.mcp.json` in the project root:

```bash
# Add MCP server config for Claude Code
```

```
.mcp.json:
{
  "mcpServers": {
    "task_manager_mcp": {
      "type": "remote",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

## Step 10 - Verification Checklist

After implementation, verify:

- [ ] `uv run python -m task_manager_mcp` starts without errors
- [ ] Server listens on `http://localhost:8000/mcp`
- [ ] MCP Inspector can connect and list 5 tools
- [ ] `capture_task` creates a task and returns it with an id
- [ ] `review_task` returns created tasks with filters
- [ ] `modify_task` updates fields correctly
- [ ] `resolve_task` marks task as done
- [ ] `remove_task` deletes the task
- [ ] Claude Code connects via `.mcp.json` and tools are available

---

## Files to Create (Summary)

```
task_manager_mcp/
  pyproject.toml            # uv init; dependencies: mcp
  src/
    task_manager_mcp/
      __init__.py
      __main__.py           # mcp.run(transport="streamable_http", port=8000)
      server.py             # FastMCP instance + store init
      models.py             # Pydantic models for Task + inputs
      store.py              # InMemoryTaskStore with thread-safe dict
      tools/
        __init__.py         # Import all tool modules
        capture.py
        review.py
        modify.py
        resolve.py
        remove.py
.mcp.json                   # Claude Code MCP config
```

Total: ~10 files, ~400-500 lines of Python.

---

## Implementation Order

1. `pyproject.toml` + install deps
2. `models.py` - all Pydantic models
3. `store.py` - InMemoryTaskStore
4. `server.py` - FastMCP init
5. `tools/capture.py`, `review.py`, `modify.py`, `resolve.py`, `remove.py`
6. `tools/__init__.py` - wire imports
7. `__main__.py` - entry point
8. `.mcp.json` - client config
9. Test with MCP Inspector
10. Test with Claude Code
