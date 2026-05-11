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

 Start server (Terminal 1):
  cd /mnt/d/coding/task-manegment-agent/task_manager_mcp
  uv run python -m src.task_manager_mcp

  Connect Claude Code (Terminal 2):
  cd /mnt/d/coding/task-manegment-agent
  claude
testing after tool creation in project 
```Prompt 
List all the MCP tools availabe to you? documents  
``` 

● You're seeing two pyproject.toml files because this is a UV workspace (monorepo) setup:

  1. Root — D:\coding\task-manegment-agent\pyproject.toml

  - Project name: task-manager-agent
  - Purpose: The main multi-agent system (OpenAI Agents SDK + FastAPI)
  - Acts as the workspace root — it declares the sub-package as a member:
  [tool.uv.workspace]
  members = ["task_manager_mcp"]

  2. Sub-package — D:\coding\task-manegment-agent\task_manager_mcp\pyproject.toml

  - Project name: task-manager-mcp
  - Purpose: The MCP server with the 5 intent-based tools (capture_task, review_task, modify_task, resolve_task, remove_task)
  - Has its own dependencies (just mcp[cli])
  - Gets managed as part of the workspace — uv resolves dependencies across both projects together

  ---
  Why this structure?

  It lets you develop two related Python packages in one repo with:
  - Shared lock file (uv.lock) — single source of truth for all dependencies
  - Independent builds — each package can be published or deployed separately
  - Clean separation — the MCP server doesn't need to import the agent code or vice versa

  So it's not duplication — it's a standard monorepo pattern with UV workspaces.
