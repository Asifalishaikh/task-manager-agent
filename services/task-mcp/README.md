# Task Manager MCP Server

An MCP (Model Context Protocol) server providing 5 intent-based task management tools: capture, review, modify, resolve, remove.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the server
uv run python -m task_manager_mcp
# → http://localhost:8000/mcp
```

## Docker

### Build

```bash
# From project root:
docker build -t task-mcp:latest -f services/task-mcp/Dockerfile services/task-mcp
```

### Run

```bash
docker run -d --name task-mcp -p 8000:8000 task-mcp:latest
```

### Verify

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

## Tools

| Tool | Description |
|------|-------------|
| `capture_task` | Create a new task from natural language |
| `review_task` | List, search, and filter tasks |
| `modify_task` | Update task fields (partial update) |
| `resolve_task` | Mark a task as completed |
| `remove_task` | Permanently delete a task |

## Architecture

```
Human → Claude Code → JSON-RPC over HTTP → task-mcp MCP Server → InMemoryTaskStore
```
