# MCP Connection Testing & Communication Flow

> **Date:** 2026-05-09  
> **Updated:** 2026-05-16 — server moved to `services/task-mcp/`  
> **Status:** Verified (all 5 tools tested against live server)  
> **Server:** task-mcp (Streamable HTTP on port 8000)

---

## 1. The .mcp.json File

Created at project root:

```json
{
  "mcpServers": {
    "task-mcp": {
      "type": "remote",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

**What it does:** Tells Claude Code "there is an MCP server running at this URL — connect to it and load its tools."

---

## 2. How to Test the Connection

### Step 1: Start the MCP Server

```bash
# From the services/task-mcp directory:
cd services/task-mcp
uv run python -m src.task_manager_mcp
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Verify Server is Alive

```bash
# In another terminal
curl http://localhost:8000/mcp -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

Expected response — SSE format listing all 5 tools.

**Important:** The `Accept` header must include both `application/json` and `text/event-stream`.

### Step 3: Launch Claude Code

```bash
# From project root (where .mcp.json lives)
claude
```

### Step 4: Verify Tools in Claude Code

Once Claude Code starts, ask:

```
List all the MCP tools available to you right now.
```

Expected: Claude Code lists all 5 tools.

### Step 5: Test a Real Tool Call

```
Capture a task called "Test Claude Code connection" with high priority.
```

Expected: Claude Code calls `capture_task` and returns a confirmation.

---

## 3. Communication Flow

```
You (Human)
    |
    v  natural language
Claude Code (Agent / Orchestrator)
    |
    v  JSON-RPC over HTTP (Streamable HTTP)
task-mcp (MCP Server)
    |
    v  in-memory operations
InMemoryTaskStore (Data)
```

### Example Walkthrough

**You say:** "Add a high priority task to review the PR"

| Step | Who | What |
|------|-----|------|
| 1 | **You** | Type natural language request |
| 2 | **Claude Code** | Parses intent, calls capture_task |
| 3 | **MCP Server** | Validates via Pydantic, calls store.create() |
| 4 | **Claude Code** | Formats response for you |
| 5 | **You** | See confirmation |

---

## 4. Testing Results (verified 2026-05-09)

| # | Tool | Result |
|---|------|--------|
| 1 | tools/list | PASS - 5 tools returned |
| 2 | capture_task | PASS - Task created with ID |
| 3 | review_task | PASS - Task shows in listing |
| 4 | modify_task | PASS - Priority updated |
| 5 | resolve_task | PASS - Resolved with timestamp |
| 6 | remove_task | PASS - Permanently removed |
| 7 | Verify empty store | PASS - "No tasks found" |

---

## 5. Notes

- **FastMCP API:** `port` and `host` go in the `FastMCP()` constructor, NOT in `.run()`
- **Transport string:** Use `"streamable-http"` (with hyphen)
- **Stateless mode:** `stateless_http=True` — no session IDs needed
- **Tool arguments:** Must be wrapped in `input: { ... }` for raw JSON-RPC (Claude Code handles this automatically)
- **SSE responses:** Server responds in SSE format — standard for Streamable HTTP

---

*End of Testing Guide*
