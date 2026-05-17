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
- **Added MCP from skills.sh:** npx skills add https://github.com/anthropics/skills --skill mcp-builder (manualy)

## Running

### Start MCP Server (Terminal 1):
```bash
cd services/task-mcp
uv run python -m src.task_manager_mcp
```

### Connect Claude Code (Terminal 2):
```bash
cd /mnt/d/coding/task-manegment-agent
claude
```

> After creating new tools, test with: *"List all the MCP tools available to you?"*

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
