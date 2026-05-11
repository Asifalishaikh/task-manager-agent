# Implementation Launch Specification — Task Manager MCP Server

> **Status:** Launch Spec  
> **Date:** 2026-05-09  
> **Informed by:** .agents/skills/mcp-builder/SKILL.md (phases 1-4 workflow)  
> **Package manager:** uv (CLI commands only)  
> **Framework:** Python FastMCP (per mcp-builder Python guide)  
> **Transport:** Streamable HTTP (per spec/mcp/transport/streamable-http-architecture.md)  

---

## 0. Decision Log — Informed by /mcp-builder

The following architectural decisions are validated against the **mcp-builder skill** (Phase 1: Deep Research and Planning):

| Decision | Choice | mcp-builder Rationale |
|----------|--------|----------------------|
| **Language** | Python | Project already uses Python 3.12.2; FastMCP has first-class support |
| **Framework** | FastMCP | Per Python Implementation Guide — @mcp.tool decorator pattern, auto schema gen |
| **Transport** | Streamable HTTP | Per Transport section — Streamable HTTP for remote servers + multi-agent need |
| **Tool naming** | {action}_task prefix | Per naming convention — clear, descriptive tool names, action-oriented naming |
| **Input models** | Pydantic v2 BaseModel | Per Python guide — all tools must use Pydantic with Field() constraints |
| **Tool annotations** | All 4 hints set | Per Quality Checklist — All tools implement annotations |
| **Response format** | Markdown | Per mcp-builder — Markdown for human-readable, optimize for agent context efficiency |
| **Error handling** | Actionable messages | Per Best Practices — Error messages should guide agents toward solutions |
| **Storage** | threading.Lock | Per concurrency note — Multiple agents calling concurrently |
| **Pagination** | limit param | Per Python guide pagination pattern |
| **Docstrings** | Comprehensive | Per Quality Checklist — All tools have comprehensive docstrings |

---

## 1. Project Structure Specification

### 1.1 New Package Layout

Create a separate MCP server package **within the monorepo** at project root:

`
task-manager-agent/
├── task_manager_mcp/              # NEW: MCP server package
│   ├── pyproject.toml             # uv-managed Python project
│   └── src/
│       └── task_manager_mcp/
│           ├── __init__.py
│           ├── __main__.py        # Entry: mcp.run(transport="streamable_http", port=8000)
│           ├── server.py          # FastMCP instance + store init + lifespan
│           ├── models.py          # Task, TaskStatus, TaskPriority + input models
│           ├── store.py           # InMemoryTaskStore (thread-safe)
│           └── tools/
│               ├── __init__.py    # Import all tool modules
│               ├── capture.py     # @mcp.tool(name="capture_task")
│               ├── review.py      # @mcp.tool(name="review_task")
│               ├── modify.py      # @mcp.tool(name="modify_task")
│               ├── resolve.py     # @mcp.tool(name="resolve_task")
│               └── remove.py      # @mcp.tool(name="remove_task")
├── .mcp.json                      # Claude Code MCP client config
└── spec/
    └── mcp/
        ├── implementation/
        │   ├── plan.md            # Existing step-by-step plan
        │   └── launch-spec.md     # THIS FILE — launch specification
        ├── tools/
        │   └── human-intent-based-tools.md
        ├── transport/
        │   └── streamable-http-architecture.md
        └── roadmap/
            └── evolution-phases.md
`

### 1.2 Rationale

- **Separate package** (not nested in src/task_manager_agent/): The MCP server is a standalone service that multiple agents connect to. It has its own dependency tree (mcp[cli] vs openai-agents). Keeping them separate avoids dependency coupling.
- **Monorepo structure**: Both packages share the same git repo. They can be developed, tested, and deployed independently.
- **uv-managed**: Each package has its own pyproject.toml and uv.lock.

---

## 2. Implementation Phases (uv CLI Commands)

### Phase A — Scaffold Package

`ash
# Step A1: Create package directory structure
mkdir -p task_manager_mcp/src/task_manager_mcp/tools

# Step A2: Initialize with uv (creates pyproject.toml, .venv, uv.lock)
cd task_manager_mcp
uv init --app --python 3.12
cd ..

# Step A3: Add MCP dependency (includes FastMCP, httpx, pydantic)
cd task_manager_mcp
uv add mcp[cli]
cd ..

# Step A4: Create all scaffold files
touch task_manager_mcp/src/task_manager_mcp/__init__.py
touch task_manager_mcp/src/task_manager_mcp/tools/__init__.py
`

**Verification checkpoint:**
`ash
cd task_manager_mcp
uv run python -c "import mcp; print(mcp.__version__)"
cd ..
`

---

### Phase B — Data Models

**File:** 	ask_manager_mcp/src/task_manager_mcp/models.py

**What to implement:**
- TaskStatus enum: not_started, in_progress, done, cancelled
- TaskPriority enum: low, medium, high, critical
- Task model with fields: id, title, description, status, priority, assignee, tags, created_at, updated_at, resolved_at
- Input models for each of the 5 tools: CaptureTaskInput, ReviewTaskInput, ModifyTaskInput, ResolveTaskInput, RemoveTaskInput

**Spec requirements:**
- Use rom __future__ import annotations for deferred evaluation
- Use pydantic.BaseModel with model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
- Every field must have description= with examples
- Constraints on all fields: min_length, max_length, ge, le, max_items
- Use datetime (not str) for timestamp fields
- Task.resolved_at is datetime | None
- tags field: list[str] with max_length=10
- Input model for remove_task includes reason field for audit trail

**Verification checkpoint:**
`ash
cd task_manager_mcp
uv run python -c "from src.task_manager_mcp.models import Task, TaskStatus, TaskPriority, CaptureTaskInput, ReviewTaskInput, ModifyTaskInput, ResolveTaskInput, RemoveTaskInput; print('Models OK')"
cd ..
`

---

### Phase C — Storage Layer

**File:** 	ask_manager_mcp/src/task_manager_mcp/store.py

**What to implement:**
- InMemoryTaskStore class with 	hreading.Lock
- Internal dict[str, Task] as storage
- Methods: create(data), list(filters), get(task_id), update(task_id, data), resolve(task_id, note), delete(task_id)

**Spec requirements:**
- create() generates UUID v4 via uuid.uuid4().hex
- create() auto-sets created_at and updated_at to datetime.now()
- list() supports: status, priority, assignee, tag filters (exact match)
- list() supports: query for full-text search across title and description
- list() returns sorted by created_at descending
- update() only sets provided fields (partial update pattern)
- update() auto-sets updated_at to datetime.now()
- resolve() sets status=done, resolved_at=datetime.now()
- resolve() stores resolution_note in description append
- delete() removes from dict; raises KeyError if not found
- All methods acquire/release self._lock for thread safety

**Verification checkpoint:**
`ash
cd task_manager_mcp
uv run python -c "
from src.task_manager_mcp.store import InMemoryTaskStore
s = InMemoryTaskStore()
t = s.create({'title': 'Test task', 'priority': 'high'})
assert t.id is not None
assert s.get(t.id).title == 'Test task'
s.resolve(t.id, 'Done')
assert s.get(t.id).status.value == 'done'
s.delete(t.id)
print('Store OK')
"
cd ..
`

---

### Phase D — Server Bootstrap

**Files:**
- 	ask_manager_mcp/src/task_manager_mcp/server.py
- 	ask_manager_mcp/src/task_manager_mcp/__main__.py

**server.py requirements:**
- Initialize mcp = FastMCP("task_manager_mcp")
- Initialize a singleton store = InMemoryTaskStore()
- Import all tool modules (they self-register via @mcp.tool decorator)
- No if __name__ == "__main__" guard (it is a module, not entry point)

**__main__.py requirements:**
- Import mcp from .server
- Call mcp.run(transport="streamable_http", port=8000)
- This is the sole entry point

**Verification checkpoint:**
`ash
cd task_manager_mcp
uv run python -c "from src.task_manager_mcp.server import mcp; print(f'Server: {mcp.name}')"
cd ..
`

---

### Phase E — Tool Implementations (5 tools)

Each tool follows this invariant pattern informed by mcp-builder:

`
@mcp.tool(
    name="{action}_task",
    annotations={...}
)
async def {action}_task(input: {Action}TaskInput) -> str:
    '''Comprehensive docstring.'''
    try:
        result = store.{method}(...)
        return markdown_format(result)
    except Exception as e:
        return f"Error: {actionable_message}"
`

#### Tool E1 — capture_task (tools/capture.py)
- **annotation:** readOnlyHint: False, destructiveHint: False, idempotentHint: False
- **behavior:** Receives CaptureTaskInput -> calls store.create() -> returns markdown with task id, title, timestamps
- **returns:** Human-readable confirmation with task ID
- **edge case:** Validation errors handled by Pydantic

#### Tool E2 — review_task (tools/review.py)
- **annotation:** readOnlyHint: True, destructiveHint: False, idempotentHint: True
- **behavior:** If query is non-empty: full-text search. Else: filter by status/priority/assignee/tag. Apply limit.
- **returns:** Markdown table of tasks or single task detail
- **edge case:** No tasks found -> "No tasks found matching your criteria."

#### Tool E3 — modify_task (tools/modify.py)
- **annotation:** readOnlyHint: False, destructiveHint: False, idempotentHint: True
- **behavior:** Receives ModifyTaskInput -> calls store.update(). Tag merging: if tags provided replace all; if add_tags/remove_tags merge.
- **returns:** Updated task in markdown
- **edge case:** Invalid task_id -> "Error: Task not found: {task_id}"

#### Tool E4 — resolve_task (tools/resolve.py)
- **annotation:** readOnlyHint: False, destructiveHint: False, idempotentHint: True
- **behavior:** Calls store.resolve() -> sets status=done, records timestamp
- **returns:** Confirmation with task ID, title, completion time
- **edge case:** Already done -> idempotent no-op is acceptable

#### Tool E5 — remove_task (tools/remove.py)
- **annotation:** readOnlyHint: False, destructiveHint: True, idempotentHint: False
- **behavior:** Calls store.delete() -> removes from store
- **returns:** "Task '{title}' ({task_id}) has been permanently removed."
- **edge case:** Already deleted or invalid -> "Error: Task not found: {task_id}"

**Verification checkpoint (all 5 tools registered):**
`ash
cd task_manager_mcp
uv run python -c "
from src.task_manager_mcp.server import mcp
tools = mcp._tool_manager.tools
assert len(tools) == 5, f'Expected 5 tools, got {len(tools)}'
names = [t.name for t in tools.values()]
assert 'capture_task' in names
assert 'review_task' in names
assert 'modify_task' in names
assert 'resolve_task' in names
assert 'remove_task' in names
print(f'All 5 tools registered: {names}')
"
cd ..
`

---

### Phase F — Wire Tools (tools/__init__.py)

**File:** 	ask_manager_mcp/src/task_manager_mcp/tools/__init__.py

**Contents spec:**
`python
from . import capture
from . import review
from . import modify
from . import resolve
from . import remove
`

The server module imports 	ools which triggers decorator registration.

---

### Phase G — Claude Code Integration (.mcp.json)

**File:** .mcp.json at project root

**Contents:**
`json
{
  "mcpServers": {
    "task_manager_mcp": {
      "type": "remote",
      "url": "http://localhost:8000/mcp"
    }
  }
}
`

**Usage:**
1. Start MCP server: cd task_manager_mcp && uv run python -m task_manager_mcp
2. Claude Code auto-detects .mcp.json and connects
3. Tools appear in Claude's tool list

---

## 3. Testing Specification

### 3.1 MCP Inspector (Manual Testing)

`ash
# Terminal 1: Start the server
cd task_manager_mcp
uv run python -m task_manager_mcp
# -> Server starts at http://localhost:8000/mcp

# Terminal 2: Launch MCP Inspector
npx @modelcontextprotocol/inspector

# In Inspector UI:
# - Set transport URL to: http://localhost:8000/mcp
# - List tools (should show 5 tools)
# - Test each tool with sample inputs
`

### 3.2 curl Functional Test Sequence

`ash
# Test 1: Capture a task
curl -X POST http://localhost:8000/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"capture_task\",\"arguments\":{\"title\":\"Review deployment pipeline\",\"priority\":\"high\",\"tags\":[\"devops\",\"deploy\"]}}}"

# Test 2: Review all tasks
curl -X POST http://localhost:8000/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"review_task\",\"arguments\":{}}}"

# Test 3: Modify task (use ID from Test 1 response)
curl -X POST http://localhost:8000/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"modify_task\",\"arguments\":{\"task_id\":\"<ID>\",\"priority\":\"critical\"}}}"

# Test 4: Resolve task
curl -X POST http://localhost:8000/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"resolve_task\",\"arguments\":{\"task_id\":\"<ID>\",\"resolution_note\":\"Pipeline verified and green\"}}}"

# Test 5: Remove task
curl -X POST http://localhost:8000/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"remove_task\",\"arguments\":{\"task_id\":\"<ID>\",\"reason\":\"Test cleanup\"}}}"
`

---

## 4. mcp-builder Quality Checklist

Before implementation is complete, verify against the mcp-builder Quality Checklist:

### Strategic Design
- [ ] Tools enable complete workflows (create -> review -> modify -> resolve -> remove)
- [ ] Tool names reflect natural task subdivisions (capture_task, not create_task)
- [ ] Response formats optimize for agent context efficiency
- [ ] Error messages guide agents toward correct usage

### Implementation Quality
- [ ] All 5 tools implemented with descriptive names and docstrings
- [ ] Return types are consistent (all return str)
- [ ] Error handling for all external calls (store operations)
- [ ] Server name follows format: task_manager_mcp
- [ ] All I/O operations use async/await
- [ ] Common functionality extracted (response formatting)
- [ ] Error messages are clear, actionable, educational

### Tool Configuration
- [ ] All tools implement name and annotations in the decorator
- [ ] Annotations correctly set per spec table
- [ ] All tools use Pydantic BaseModel for input validation with Field() definitions
- [ ] All Pydantic Fields have explicit types and descriptions with constraints
- [ ] All tools have comprehensive docstrings with input/output types

### Code Quality
- [ ] File includes proper imports (stdlib, third-party, local grouping)
- [ ] Filtering options provided for review_task
- [ ] All async functions defined with async def
- [ ] Type hints used throughout
- [ ] Constants defined at module level in UPPER_CASE

### Testing
- [ ] uv run python -m task_manager_mcp starts without errors
- [ ] All imports resolve correctly
- [ ] MCP Inspector connects and lists 5 tools
- [ ] Sample tool calls work as expected
- [ ] Error scenarios handled gracefully

---

## 5. Git Branch Strategy

Use **feature branches** — not worktrees.

### Branch Workflow

```
master              (stable specs, released code)
    │
    ├── feature/mcp-server      ← YOU ARE HERE: build the MCP server
    │       │
    │       ├── Phase A (scaffold)
    │       ├── Phase B (models)
    │       ├── Phase C (store)
    │       ├── Phase D (server)
    │       ├── Phase E (tools)
    │       ├── Phase F (wire)
    │       └── Phase G (.mcp.json)
    │
    └── merge back to master when all phases pass verification
```

### Commands

```bash
# Create the feature branch off master
git checkout -b feature/mcp-server

# Work through phases A-G, committing after each verified phase
git add task_manager_mcp/ .mcp.json spec/mcp/testing/connection-testing.md
git commit -m "feat: add MCP server package scaffold (Phase A)"

# Keep the spec updates on master separate
git add spec/mcp/implementation/launch-spec.md spec/mcp/testing/
git commit -m "docs: add launch spec and testing guide"

# When all phases are complete and verified:
git checkout master
git merge feature/mcp-server
```

### Why branches (not worktrees)

| Approach | Verdict | Reason |
|----------|---------|--------|
| **Branches** | ✅ Preferred | Single working directory, simple `git merge`, no confusion |
| Worktrees | ❌ Avoid | Unnecessary complexity for a monorepo; branches achieve the same isolation |

---

## 6. Future-Proofing Decisions

| Future Phase | Decision Made Now | Why It Helps |
|-------------|-------------------|--------------|
| **Phase 2 — Database** | InMemoryTaskStore implements consistent interface | Swapping to DatabaseTaskStore only needs new class |
| **Phase 3 — User concept** | assignee field already on Task | User ownership maps naturally to assignee |
| **Phase 4 — Auth** | Streamable HTTP transport | Auth middleware wraps ASGI app without touching tools |
| **Phase 5 — K8s** | Stateless design (store swappable) | Horizontal scale-out when store becomes database-backed |

**Design guidance for store interface (protocol):**

The InMemoryTaskStore should implement this conceptual interface so Phase 2 is a drop-in replacement:
- create(data: dict) -> Task
- get(task_id: str) -> Task | None
- list(query: str, status: str, priority: str, assignee: str, tag: str, limit: int) -> list[Task]
- update(task_id: str, data: dict) -> Task
- resolve(task_id: str, note: str) -> Task
- delete(task_id: str) -> None

---

## 7. Execution Order

| Step | Phase | Action | Time Est. |
|------|-------|--------|-----------|
| 1 | A | Scaffold package with uv init + uv add mcp | 2 min |
| 2 | B | Implement models.py (enums + all Pydantic models) | 15 min |
| 3 | C | Implement store.py (InMemoryTaskStore) | 20 min |
| 4 | D | Implement server.py + __main__.py | 10 min |
| 5 | E1 | Implement tools/capture.py | 10 min |
| 6 | E2 | Implement tools/review.py | 15 min |
| 7 | E3 | Implement tools/modify.py | 15 min |
| 8 | E4 | Implement tools/resolve.py | 10 min |
| 9 | E5 | Implement tools/remove.py | 10 min |
| 10 | F | Wire tools/__init__.py | 2 min |
| 11 | G | Create .mcp.json at project root | 1 min |
| 12 | H | Test with MCP Inspector + curl | 15 min |
| 13 | I | Connect Claude Code via .mcp.json | 5 min |
| 14 | J | Run mcp-builder Quality Checklist validation | 10 min |

**Total estimated time: ~2 hours**

---

## 8. Rollback Plan

If any phase fails verification:
1. **Stop** — Do not proceed to next phase
2. **Identify** — Note which verification checkpoint failed
3. **Re-plan** — Update this spec with the fix before re-executing
4. **Retry** — From the failing phase

---

## 9. Skills Integration

This implementation follows the mcp-builder skill's 4-phase workflow:

`
mcp-builder Phase 1 (Research & Planning)
    |
    v
This spec (Launch Spec — maps decisions to implementation)
    |
    v
mcp-builder Phase 2 (Implementation — actual code)
    |
    v
mcp-builder Phase 3 (Review & Test — MCP Inspector + checklist)
    |
    v
mcp-builder Phase 4 (Evaluations — future phase)
`

The mcp-builder skill's Python Implementation Guide should be loaded alongside this spec during the code-writing phase for exact patterns on FastMCP decorators, Pydantic models, and error handling.

---

*End of Launch Specification*
