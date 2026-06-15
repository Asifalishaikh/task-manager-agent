# Task Manager Agent

A multi-agent task management system using OpenAI Agents SDK and FastAPI.

## Project Overview

An end-to-end task management system built in progressive milestones:

| # | Milestone | Status | What |
|---|-----------|--------|------|
| 1 | **MCP Server** | ✅ Complete | 5 intent-based tools (capture, review, modify, resolve, remove) with in-memory storage |
| 2 | **Docker + CI + Registry** | ✅ Complete | Multi-stage Docker images auto-built on push to ghcr.io for both services |
| 3 | **Agent SDK Research** | ✅ Complete | Studied `Agent` vs `SandboxAgent` — documented in ADR and spec |
| 4 | **Agent Testing** | ✅ Complete | Simple Agent (Gemini + MCP) tested. SandboxAgent (Docker + MCP + Gemini) tested |
| 5 | **K8s Deployment** | ✅ Complete | Both services deployed to Docker Desktop K8s, tested end-to-end |

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
    ├── MCP Server (2 replicas)
    └── SandboxAgent (sidecar) ──► DockerSandboxClient
```

### Decision Path

```
OpenAI Agents SDK
    ├── Agent (Simple Agent) ── CLI, MCP calls, task CRUD
    └── SandboxAgent          ── Filesystem, Shell, Docker-in-Docker
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

### ✅ Milestone 2: Multi-Stage Docker Build + CI + Registry
Containerize services and automate build + push to registry.

**MCP Server:**
| Area | Detail |
|------|--------|
| **Dockerfile** | `services/task-mcp/Dockerfile` — multi-stage, non-root user, HEALTHCHECK |
| **Registry** | `ghcr.io/asifalishaikh/task-manager-agent/task-manager-mcp` |
| **CI + Registry** | `.github/workflows/task-mcp-build.yml` — auto-build on `services/task-mcp/**` changes |
| **Verified** | Image built, container run, `tools/list` returns 5 tools ✅ |

**SandboxAgent:**
| Area | Detail |
|------|--------|
| **Dockerfile** | `services/task-manager-agent/Dockerfile` — multi-stage, non-root user |
| **Registry** | `ghcr.io/asifalishaikh/task-manager-agent/task-sandbox-agent` |
| **CI + Registry** | `.github/workflows/task-agent-build.yml` — auto-build on `services/task-manager-agent/**` changes |
| **Verified** | Image built, modules verified, pushed to ghcr.io ✅ |

**Run comparison:**
| | Local (uv) | Docker |
|---|---|---|
| Command (MCP) | `uv run python -m task_manager_mcp` | `docker run -p 8000:8000 task-mcp:latest` |
| Command (Agent) | `uv run python -m task_manager_agent.sandbox_agent "prompt"` | `docker run --network host -v /var/run/docker.sock:/var/run/docker.sock -e GEMINI_API_KEY=xxx task-agent:latest "prompt"` |
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

### ✅ Milestone 4: Agent Testing & Validation
All agents tested end-to-end with Gemini 3.1 Flash-Lite + LiteLLM.

| Test | Script | Ran in Docker? |
|------|--------|---------------|
| Simple Agent + MCP | `test_mcp.py` | ❌ Agent runs directly on host. Connects to MCP server on localhost. |
| SandboxAgent + Docker + MCP | `sandbox_agent.py` | ✅ Agent runs inside Docker container via `DockerSandboxClient` |

### Known Limitation
Sandbox built-in capabilities (Filesystem, Shell) require **OpenAI Responses API** — they don't work with Gemini via LiteLLM (uses ChatCompletions). MCP tools work with both.

---

### ✅ Milestone 5: Kubernetes Deployment (Docker Desktop)
Both services deployed to local K8s cluster with security hardening.

| Area | Detail |
|------|--------|
| **Namespace** | `task-manager` — isolated environment for all resources |
| **MCP Server** | 2 replicas, ClusterIP service, ConfigMap for settings |
| **SandboxAgent** | 1 replica, Docker socket mounted, sleeps for exec access |
| **Secrets** | Generated from `.env` → base64 encoded → K8s Secret (never committed) |
| **Internal DNS** | `task-mcp-service.task-manager.svc.cluster.local:8000` |
| **securityContext** | Pod-level: `runAsNonRoot`, `runAsUser: 1001`. Container: `allowPrivilegeEscalation: false`, `capabilities.drop: ALL` |
| **RBAC** | Not needed — no service calls the K8s API |

**Verified:**
- MCP tools reachable via curl and SDK from inside SandboxAgent pod ✅
- All 5 tools discovered: capture, review, modify, resolve, remove ✅
- Env vars correctly injected from Secret ✅

**Manifests:** `Deployments/k8s/`

---

### 🔜 Next: Database Persistence
Build a CLI agent that call MCP tools via OpenAI SDK's `Agent` + `MCPServer`.

**Plan:** `agent.py` → CLI runner `main.py` → End-to-end test

### 📅 Future: Database, Auth, K8s
See `spec/mcp/roadmap/evolution-phases.md` for full roadmap.

---

## Key Documents

| File | Purpose |
|------|---------|
| **`Progress.md`** | Task-level milestone tracking — checkboxes for every item built |
| **`docs/adrs/agent-decision.md`** | ADR-001: Simple Agent vs SandboxAgent |
| **`docs/adrs/k8s-deployment-decisions.md`** | ADR-002: K8s deployment decisions (security, RBAC, secrets, sleep) |
| **`spec/mcp/`** | MCP server specifications — transport, tools, implementation plan, testing, roadmap |
| **`spec/agents/sandbox-agent-spec.md`** | SandboxAgent specification — architecture, capabilities, Docker client, CLI usage |
| **`AGENTS.md`** | Agent workflow documentation — creator workflow, verification, TDD standards |

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

## CI + Registry — GitHub Actions

Every push to `master` triggers automatic build + push to ghcr.io for the affected services. Note: this is **Continuous Integration + delivery to registry** — full Continuous Deployment (auto-deploy to a live server) will be added in Part 3 (K8s phase).

| File | Service | Triggers on |
|------|---------|-------------|
| `.github/workflows/task-mcp-build.yml` | MCP Server | `services/task-mcp/**` changes |
| `.github/workflows/task-agent-build.yml` | SandboxAgent | `services/task-manager-agent/**` changes |

| File | Purpose |
|------|---------|
| `.github/workflows/task-mcp-build.yml` | Builds Docker image, pushes to ghcr.io (CI + registry only, no auto-deploy) |

**Automatic tags:**
| Trigger | Tag |
|---------|-----|
| Push to `master` | `master`, `sha-<commit>` |
| Git tag `v*` (release) | `v0.1.0`, `latest` |
| Pull request | Build only (no push) |

**Latest published images:**
```
# MCP Server
docker pull ghcr.io/asifalishaikh/task-manager-agent/task-manager-mcp:master

# SandboxAgent
docker pull ghcr.io/asifalishaikh/task-manager-agent/task-sandbox-agent:master
```

**Why ghcr.io instead of Docker Hub?**
- Unlimited private repositories (Docker Hub limits to 1)
- Native GitHub integration — same repo, same GITHUB_TOKEN, no extra login
- Permissions inherit from repo access automatically
- Images visible under "Packages" on the GitHub repo sidebar

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
| **Phase 5** | Production K8s (cloud cluster, HPA, Helm) | Move beyond Docker Desktop |

### Deploying to K8s (Current Dev Setup)

API keys are stored in `.env` (local, `.gitignore`). For K8s deployment:

```bash
# Generate secret.yaml from .env (auto base64 encoded)
kubectl create secret generic task-sandbox-secret \
  --from-env-file=.env \
  --namespace=task-manager \
  --dry-run=client -o yaml > secret.yaml

# Apply to cluster
kubectl apply -f secret.yaml
```

> `secret.yaml` is **never committed** to GitHub — add to `.gitignore`.
> Production: use Sealed Secrets or External Secrets Operator instead.

---

## Development vs Production Files

This project contains files for two purposes. During the learning phase, keep all files. For production deployment, only the **Production** files are needed.

### ✅ Production Files (needed to run services)

| Category | Files |
|----------|-------|
| **MCP Server** | `services/task-mcp/Dockerfile`, `.dockerignore`, `pyproject.toml` |
| | `services/task-mcp/src/task_manager_mcp/__init__.py`, `__main__.py`, `server.py`, `models.py`, `store.py` |
| | `services/task-mcp/src/task_manager_mcp/tools/capture.py`, `modify.py`, `remove.py`, `resolve.py`, `review.py` |
| **Agent Service** | `services/task-manager-agent/pyproject.toml` |
| | `services/task-manager-agent/src/task_manager_agent/__init__.py`, `main.py`, `sandbox_agent.py` |
| **Root Config** | `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `.mcp.json`, `.env.example` |
| **Documentation** | `README.md`, `AGENTS.md`, `CLAUDE.md` |

### 🧪 Development / Learning Files (not needed in production)

| File | Purpose |
|------|---------|
| `services/task-manager-agent/src/task_manager_agent/hello_gemini.py` | Standalone test — Gemini model via LiteLLM |
| `services/task-manager-agent/src/task_manager_agent/test_mcp.py` | Test — Simple Agent with MCP tools |
| `Progress.md` | Project milestone tracking |
| `docs/adrs/agent-decision.md` | Architecture Decision Record |
| `docs/architecture.excalidraw` | Architecture diagram source |
| `spec/` (entire directory) | Specifications for agents, MCP, transport, roadmap |
| `.agents/` | Claude Code skill files (mcp-builder, multi-stage-dockerfile) |
| `.claude/` | Claude Code local settings and skills |
| `.github/workflows/task-mcp-build.yml` | GitHub Actions CI + registry for MCP server |
| `.github/workflows/task-agent-build.yml` | GitHub Actions CI + registry for SandboxAgent |
| `skills-lock.json` | Claude Code skill lock file |
| `__pycache__/` (any directory) | Python bytecode cache (auto-generated) |

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
