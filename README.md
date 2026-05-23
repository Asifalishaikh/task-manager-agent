# Task Manager Agent

A multi-agent task management system using OpenAI Agents SDK and FastAPI.

## Architecture Diagram

The system architecture is designed using [Excalidraw](https://excalidraw.com).

📐 **[View the architecture diagram →](docs/architecture.excalidraw)**

To open it:
1. Go to [excalidraw.com](https://excalidraw.com)
2. Click **Open** → **Open file**
3. Select `docs/architecture.excalidraw`
4. Edit and re-export as needed

## Project Setup

- **Python:** 3.12.2
- **Package Manager:** [uv](https://docs.astral.sh/uv/)
- **Agent Framework:** OpenAI Agents SDK
- **API:** FastAPI + Uvicorn
- **Deployment Target:** Kubernetes (K8s)
- **Multi-stage Dockerfile:** `services/task-mcp/Dockerfile` (builder + runtime stages, non-root user, HEALTHCHECK)
- **Added MCP from skills.sh:** `npx skills add https://github.com/anthropics/skills --skill mcp-builder` (manual)

## Running

### 1. Start MCP Server (Terminal 1):
```bash
cd services/task-mcp
uv run python -m task_manager_mcp
# → Server starts at http://localhost:8000/mcp
```

### 2. Test MCP Tools (Terminal 2):
Open a **new terminal** and ask Claude Code (or any MCP client connected to the server):

> *"List all the MCP tools available to you?"*

You should see the 5 intent-based tools:
| Tool | Purpose |
|------|---------|
| `capture_task` | Create a new task |
| `review_task` | List / search / filter tasks |
| `modify_task` | Update existing task fields |
| `resolve_task` | Mark a task as completed |
| `remove_task` | Delete a task permanently |

### 3. Connect Claude Code (Terminal 2, alternative):
```bash
cd /mnt/d/coding/task-manegment-agent
claude
# or: source ~/.bashrc && claude-ds (deepseek)
```

---

## Docker (Multi-Stage Build)

A production-ready multi-stage Dockerfile is at `services/task-mcp/Dockerfile`.

| Stage | Base Image | Purpose |
|-------|-----------|---------|
| `builder` | `python:3.12-slim` + `uv` | Install deps, compile bytecode, verify tools |
| `runtime` | `python:3.12-slim` | Minimal image, non-root user, HEALTHCHECK |

### Quick Start

```bash
# Build from project root
docker build -t task-mcp:latest -f services/task-mcp/Dockerfile services/task-mcp

# Run (background)
docker run -d --name task-mcp -p 8000:8000 task-mcp:latest

# Verify
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

> See `services/task-mcp/README.md` for full details.

---

## Run Method Comparison: Python/uv vs Docker

You can run the MCP server two ways — here's how they compare:


  Run Method Comparison — side-by-side table of uv run python vs docker run:

  ┌───────────────┬───────────────────────────────────┬─────────────────────────────────────────┐
  │               │        Local (uv + Python)        │                 Docker                  │
  ├───────────────┼───────────────────────────────────┼─────────────────────────────────────────┤
  │ Command       │ uv run python -m task_manager_mcp │ docker run -p 8000:8000 task-mcp:latest │
  ├───────────────┼───────────────────────────────────┼─────────────────────────────────────────┤
  │ Pre-requisite │ Python 3.12 + uv                  │ Docker only                             │
  ├───────────────┼───────────────────────────────────┼─────────────────────────────────────────┤
  │ Build step    │ None      run directly from source│ docker build required first             │
  ├───────────────┼───────────────────────────────────┼─────────────────────────────────────────┤
  │ Isolation     │ Uses System Python, shared env    │ Fully isolated evnviornment             │
  └───────────────┴───────────────────────────────────┴─────────────────────────────────────────┘
  │ Best for      │ Development                       │ Production / CI/CD                      │
  └───────────────┴───────────────────────────────────┴─────────────────────────────────────────┘



  ┌───────────────────────────────────┬────────────────────────────────────────────┐
  │          Without Docker           │                With Docker                 │
  ├───────────────────────────────────┼────────────────────────────────────────────┤
  │ Need Python 3.12 + uv installed   │ Just need Docker                           │
  ├───────────────────────────────────┼────────────────────────────────────────────┤
  │ uv run python -m task_manager_mcp │ docker run -p 8000:8000 task-mcp:latest    │
  ├───────────────────────────────────┼────────────────────────────────────────────┤
  │ Only runs on your machine         │ Runs anywhere (your laptop, a server, K8s) │
  ├───────────────────────────────────┼────────────────────────────────────────────┤
  │ No health checks                  │ Built-in HEALTHCHECK                       │
  ├───────────────────────────────────┼────────────────────────────────────────────┤
  │ Runs as root                      │ Runs as non-root user (security)           │
---   
 The multi-stage part means it builds in two steps:
  1. builder stage — Installs all dependencies + compiles code (bigger image, all build tools)
  2. runtime stage — Copies only the final app into a clean, minimal Python image (smaller, safer)
## Roadmap

### 🔄 Current — Task Manager Agent (Multi-Agent Orchestrator)

Build the orchestrator agent that connects the user to the MCP tools:

| Step | What | Key Files |
|------|------|-----------|
| **1** | **Agent setup** — Create Task Manager Agent using OpenAI Agents SDK, connected to `task-mcp` server via `MCPServer` class (auto-discovers tools) | `agent.py` |
| **2** | **FastAPI server** — Build `/chat` endpoint that accepts user messages and returns agent responses | `main.py` |
| **3** | **End-to-end flow** — User → HTTP request → Agent → MCP tools → Response. Test the full chain. | Tests, docs |

Architecture:
```
User → POST /chat → FastAPI → Task Manager Agent (OpenAI SDK)
                                        ↓
                              MCP Client ←→ MCP Server (:8000)
                                                ↓
                                         InMemoryTaskStore
```

### 📅 Future Phases (from `spec/mcp/roadmap/evolution-phases.md`)

| Phase | What | Why |
|-------|------|-----|
| **Phase 2** | Database Persistence (SQLite → PostgreSQL) | Tasks survive restarts |
| **Phase 3** | User Concept (owner field, scoped queries) | Multi-user support |
| **Phase 4** | Auth Enforcement (API keys / JWT) | Secure access |
| **Phase 5** | Kubernetes Deployment | Production scaling |

---

## Monorepo Structure

This project uses **uv workspaces** (standard monorepo pattern):

```
Root (task-manager-agent)
├── services/
│   ├── task-mcp/                    # MCP server (5 intent-based tools)
│   │   └── pyproject.toml           # name: task-manager-mcp
│   └── task-manager-agent/          # Multi-agent orchestrator
│       └── pyproject.toml           # name: task-manager-agent
├── pyproject.toml                   # Workspace root
└── uv.lock                          # Single lock file
```

Why this structure?
- **Shared lock file** — single source of truth for all dependencies
- **Independent builds** — each package deployed separately
- **Clean separation** — MCP server doesn't import agent code or vice versa
