# Task Manager Agent

A multi-agent task management system using OpenAI Agents SDK and FastAPI.

## Project Overview

An end-to-end task management system built in progressive milestones:

| # | Milestone | Status | What |
|---|-----------|--------|------|
| 1 | **MCP Server** | ✅ Complete | 5 intent-based tools (capture, review, modify, resolve, remove) with in-memory storage |
| 2 | **Docker + CI/CD** | ✅ Complete | Multi-stage Docker image auto-built on push to `ghcr.io/asifalishaikh/task-manager-agent/task-manager-mcp` |
| 3 | **Agent SDK Research** | ✅ Complete | Studied `Agent` vs `SandboxAgent` — documented in ADR and spec |
| 4 | **SandboxAgent** | 🚧 Built / Untested | Docker-backed agent with Filesystem + Shell capabilities + MCP tools |
| 5 | **Simple Agent CLI** | 🔜 Next | Connect user via CLI → Simple Agent → MCP tools → Response |
| 6 | **Kubernetes** | 📅 Future | SandboxAgent inside K8s pods with DockerSandboxClient |

## System Architecture

### Current State

```
Terminal / Claude Code
       │
       ├── MCP Protocol ────────► MCP Server (:8000) ──► InMemoryTaskStore
       │                            (task-manager-mcp)
       │
       ├── GitHub Actions ──────► Docker Build ──► ghcr.io (CI/CD)
       │
       └── SandboxAgent ────────► DockerSandboxClient ──► Docker Container
                                    (Filesystem + Shell + MCP tools)
```

### Future State

```
User ──► CLI / API
            │
            ▼
    Simple Agent (Agent + MCPServer)
            │
            ├──► MCP Server (:8000) ──► Task Store
            │
            └──► SandboxAgent ──► DockerSandboxClient ──► Container
                                    (Filesystem, Shell, Skills, Memory)

K8s Pod:
    ├── Simple Agent (HTTP server)
    └── SandboxAgent (sidecar) ──► DockerSandboxClient
```

### Decision Path

```
OpenAI Agents SDK
    ├── Agent (Simple Agent) ── "Use now" ── CLI, MCP calls, task CRUD
    └── SandboxAgent          ── "Use later" ── Filesystem, Shell, K8s
            └── DockerSandboxClient ── Container isolation ──► K8s
```

---

## Project Milestones

### ✅ Milestone 1: MCP Server (5 Intent-Based Tools)
Implement an MCP server with CRUD tools for task management, all in-memory.

| Tool | Description | File |
|------|-------------|------|
| `capture_task` | Create a new task | `services/task-mcp/src/task_manager_mcp/tools/capture.py` |
| `review_task` | List / search / filter tasks | `services/task-mcp/src/task_manager_mcp/tools/review.py` |
| `modify_task` | Update task fields | `services/task-mcp/src/task_manager_mcp/tools/modify.py` |
| `resolve_task` | Mark task completed | `services/task-mcp/src/task_manager_mcp/tools/resolve.py` |
| `remove_task` | Delete task permanently | `services/task-mcp/src/task_manager_mcp/tools/remove.py` |

**Docs:** `spec/mcp/` — transport, tools, implementation plan, testing, roadmap

---

### ✅ Milestone 2: Multi-Stage Docker Build + CI/CD
Containerize and automate the MCP server deployment.

| Area | Detail |
|------|--------|
| **Dockerfile** | Multi-stage (builder + runtime), non-root user, HEALTHCHECK |
| **Registry** | `ghcr.io/asifalishaikh/task-manager-agent/task-manager-mcp` |
| **CI/CD** | `.github/workflows/task-mcp-ci.yml` — auto-build on `services/task-mcp/**` changes |
| **Verified** | Image built, container run, `tools/list` returns 5 tools ✅ |

**Run comparison:**
| | Local (uv) | Docker |
|---|---|---|
| Command | `uv run python -m task_manager_mcp` | `docker run -p 8000:8000 task-mcp:latest` |
| Best for | Development | Production / CI/CD |

---

### ✅ Milestone 3: OpenAI Agents SDK Research
Deep-dive study of the SDK to decide agent architecture.

| Area | Finding | Doc |
|------|---------|-----|
| **Agent types** | `Agent` (Simple) vs `SandboxAgent` | `docs/adrs/agent-decision.md` |
| **Decision** | Simple Agent now, SandboxAgent for K8s | ADR-001 |
| **Sandbox clients** | `UnixLocalSandboxClient`, `DockerSandboxClient`, hosted | `spec/agents/sandbox-agent-spec.md` |
| **Capabilities** | `Filesystem`, `Shell`, `Memory`, `Skills`, `Compaction` | SDK docs |

---

### ✅ Milestone 4: SandboxAgent Prototype
Docker-backed SandboxAgent combining MCP tools + filesystem + shell.

| Component | Detail |
|-----------|--------|
| **Agent** | `SandboxAgent` with `Filesystem` + `Shell` capabilities |
| **Client** | `DockerSandboxClient` for container isolation |
| **MCP** | Connects to MCP server via `host.docker.internal:8000/mcp` |
| **Manifest** | Mounts project files, creates scratch workspace |
| **File** | `services/task-manager-agent/src/task_manager_agent/sandbox_agent.py` |

---

### 🔜 Next: Simple Agent CLI
Build a CLI agent that call MCP tools via OpenAI SDK's `Agent` + `MCPServer`.

**Plan:** `agent.py` → CLI runner `main.py` → End-to-end test

### 📅 Future: Database, Auth, K8s
See `spec/mcp/roadmap/evolution-phases.md` for full roadmap.

---

## Project Setup

- **Python:** 3.12.2
- **Package Manager:** [uv](https://docs.astral.sh/uv/)
- **Agent Framework:** OpenAI Agents SDK v0.15.1
- **API:** FastAPI + Uvicorn
- **Container Registry:** ghcr.io (GitHub Container Registry)
- **CI/CD:** GitHub Actions (path-filtered per service)
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
```bash
# Ask Claude Code connected to the MCP server:
"List all the MCP tools available to you?"
```

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

### 🔜 Current — Simple Agent CLI

Build a CLI agent that calls MCP tools via OpenAI SDK's `Agent` + `MCPServer`.

| Step | What | Key Files |
|------|------|-----------|
| **1** | **Agent definition** — Simple `Agent` connected to `task-mcp` via `MCPServer` (auto-discovers 5 MCP tools) | `services/task-manager-agent/src/agent.py` |
| **2** | **CLI runner** — `uv run python -m task_manager_agent "Create a task: Buy groceries"` | `services/task-manager-agent/src/main.py` |
| **3** | **End-to-end test** — MCP server + agent CLI, verify tool calls | Manual test |

Architecture:
```
Terminal: uv run python -m task_manager_agent "Create a task"
                ↓
        Simple Agent (Agent + MCPServer)
                ↓
        MCP Client ←→ MCP Server (:8000)
                          ↓
                   InMemoryTaskStore
```

### ✅ Done — SandboxAgent (Code Ready, Untested)

The SandboxAgent is already written — Docker-backed with Filesystem + Shell + MCP.

| File | Purpose |
|------|---------|
| `sandbox_agent.py` | `SandboxAgent` with `DockerSandboxClient`, manifest, instruction |
| `pyproject.toml` | Optional dep `[sandbox]` = `openai-agents[docker]` |

**To test when Docker is running:**
```bash
uv sync --extra sandbox
uv run python -m task_manager_agent.sandbox_agent "Read README.md and create a task"
```

### 📅 Future Phases

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
