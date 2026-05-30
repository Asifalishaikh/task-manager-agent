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

## CI/CD — GitHub Actions

Every push to `master` that changes `services/task-mcp/**` triggers an automatic build and push.

| File | Purpose |
|------|---------|
| `.github/workflows/task-mcp-ci.yml` | Builds Docker image, pushes to ghcr.io |

**Automatic tags:**
| Trigger | Tag |
|---------|-----|
| Push to `master` | `master`, `sha-<commit>` |
| Git tag `v*` (release) | `v0.1.0`, `latest` |
| Pull request | Build only (no push) |

**Latest published image:**
```
docker pull ghcr.io/asifalishaikh/task-manager-agent/task-manager-mcp:master
```

---

## Run Method Comparison: Python/uv vs Docker

| | **Local (uv + Python)** | **Docker** |
|---|---|---|
| **Command** | `cd services/task-mcp && uv run python -m task_manager_mcp` | `docker run -p 8000:8000 task-mcp:latest` |
| **Pre-requisite** | Python 3.12 + uv installed | Docker installed |
| **Build step** | None - run directly from source | `docker build` required first |
| **Isolation** | Uses system Python, shared env | Fully isolated container |
| **Health checks** | None | Built-in HEALTHCHECK |
| **User** | Runs as your user | Non-root user (security) |
| **Best for** | Development, quick iteration | Production, CI/CD, K8s deployment |

---

## Agent Types: Agent vs SandboxAgent

The OpenAI Agents SDK provides two types of agents. Here's how they compare:

### Agent (Simple Agent)
The core building block - an LLM configured with instructions, tools, and optional runtime behavior.

```python
from agents import Agent, MCPServer

agent = Agent(
    name="Task Manager",
    instructions="You manage tasks using MCP tools.",
    mcp_servers=[MCPServer(url="http://localhost:8000/mcp")]
)
```

**What it can do:** Think, call APIs/functions, use MCP tools, hand off to other agents.

### SandboxAgent
Extends Agent with workspace isolation, filesystem access, shell commands, and skills.

```python
from agents.sandbox import SandboxAgent, Manifest, SandboxRunConfig
from agents.sandbox.capabilities import Capabilities, Filesystem, Shell

agent = SandboxAgent(
    name="Sandbox engineer",
    instructions="Read repo, edit files, run commands.",
    default_manifest=Manifest(entries={...}),
    capabilities=Capabilities.default() + [Filesystem(), Shell()]
)
```

**What it can do:** All of Agent + edit files, run shell commands, manage code repos.

### Side-by-side comparison

| Capability | Agent | SandboxAgent |
|---|---|---|
| LLM reasoning + tools | Yes | Yes |
| Function / MCP tools | Yes | Yes |
| Handoffs to other agents | Yes | Yes |
| Guardrails and structured output | Yes | Yes |
| Streaming and lifecycle hooks | Yes | Yes |
| **Filesystem access** | No | Yes (Filesystem) |
| **Shell commands** | No | Yes (Shell) |
| **Code editing** | No | Yes (apply_patch) |
| **Skills / guides** | No | Yes (Skills) |
| **Persistent workspace** | No | Yes (Manifest) |
| **Session snapshots** | No | Yes (SandboxSession) |

### Requirements

| Requirement | Agent | SandboxAgent |
|---|---|---|
| Python | 3.9+ | 3.10+ |
| Extra install | None | openai-agents[docker] (optional) |
| Sandbox client | None | UnixLocalSandboxClient or DockerSandboxClient |
| OS | All | Unix or Docker |

### Decision for this project

| Phase | Agent | When |
|-------|-------|------|
| **Now** | **Simple Agent** — call MCP tools, return responses | Immediate — build CLI first |
| **Future (K8s)** | **SandboxAgent** + `DockerSandboxClient` — agents that edit files, run commands, manage code | When we need workspace isolation + K8s parity |

**SandboxAgent is the bridge to Kubernetes.** The `DockerSandboxClient` gives us container-level isolation that maps directly to K8s pods. When we deploy to K8s, the Simple Agent runs as an HTTP service, and SandboxAgent handles file/code operations inside isolated containers.

```
K8s Pod
├── Simple Agent (HTTP server)    ← handles user chat + MCP calls
└── SandboxAgent (sandboxed)     ← handles file ops, shell commands (future)
         ↓
  DockerSandboxClient → container with Filesystem + Shell capabilities
```

---

## Roadmap

### 🔄 Current — Simple Agent CLI (No UI yet)

Build the Task Manager Agent as a CLI tool first — connect to MCP tools, test from terminal.

| Step | What | Key Files |
|------|------|-----------|
| **1** | **Agent setup** — Create `agent.py` with Simple `Agent` connected to `task-mcp` via `MCPServer` (auto-discovers 5 tools) | `services/task-manager-agent/src/agent.py` |
| **2** | **CLI runner** — Update `main.py` to run agent from terminal: `uv run python -m task_manager_agent "Capture a task: Buy groceries"` | `services/task-manager-agent/src/main.py` |
| **3** | **Test** — Start MCP server (Terminal 1), run agent CLI (Terminal 2), verify agent calls MCP tools correctly | Manual test |

Architecture:
```
Terminal: uv run python -m task_manager_agent "Create a task"
                ↓
        Task Manager Agent (Simple Agent)
                ↓
        MCP Client ←→ MCP Server (:8000)
                          ↓
                   InMemoryTaskStore
```

### 🥈 Near Future — SandboxAgent Exploration

| Step | What |
|------|------|
| **1** | Install `openai-agents[docker]` and set up `DockerSandboxClient` |
| **2** | Build a SandboxAgent with `Filesystem` + `Shell` capabilities |
| **3** | Connect SandboxAgent to our MCP tools alongside Simple Agent |
| **4** | Save sandbox state with snapshots and resume across sessions |

### 📅 Future Phases (from `spec/mcp/roadmap/evolution-phases.md`)

| Phase | What | Why |
|-------|------|-----|
| **Phase 2** | Database Persistence (SQLite → PostgreSQL) | Tasks survive restarts |
| **Phase 3** | User Concept (owner field, scoped queries) | Multi-user support |
| **Phase 4** | Auth Enforcement (API keys / JWT) | Secure access |
| **Phase 5** | Kubernetes Deployment | SandboxAgent inside K8s pods, scaling |

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
