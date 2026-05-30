# SandboxAgent Specification — Task Manager Agent

> **Status:** Draft Spec  
> **Date:** 2026-05-24  
> **Informed by:** OpenAI Agents SDK v0.15.1 (harness introduced April 2026)  
> **ADR:** `docs/adrs/agent-decision.md` — Simple Agent vs SandboxAgent decision record  
> **Package manager:** uv  
> **Sandbox client:** Docker (DockerSandboxClient)  
> **MCP transport:** Streamable HTTP  

---

## 0. Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Agent type** | SandboxAgent | Need filesystem + shell capabilities alongside MCP tools |
| **Sandbox client** | DockerSandboxClient | Container isolation - maps to K8s deployment |
| **Capabilities** | Filesystem + Shell | Read/write files + run commands |
| **MCP server URL** | `host.docker.internal:8000/mcp` | Docker container reaches host MCP server |
| **Manifest** | LocalDir + StringEntry | Mount local files + create scratch files |
| **CLI first** | `python -m` module | Keep it simple - no FastAPI until needed |
| **Python image** | Default sandbox image | SDK managed - no custom image needed initially |

---

## 1. Architecture

### 1.1 High-Level Flow

```
User (Terminal)
     |
     | uv run python -m task_manager_agent.sandbox_agent "Read file and create task"
     v
SandboxAgent (OpenAI SDK)
     |
     +-- MCPServer -----> MCP Server (task-mcp) on host:8000
     |                         |
     |                         v
     |                    InMemoryTaskStore
     |
     +-- Filesystem ----> Read/write files inside sandbox workspace
     |
     +-- Shell ---------> Run commands inside sandbox container
```

### 1.2 Container Architecture

```
+---------------------------------------------+
|             Docker Container                 |
|  (python:3.12-slim)                         |
|                                              |
|  +-------------------------------------+    |
|  |   SandboxAgent + LLM                |    |
|  |                                     |    |
|  |  Capabilities:                      |    |
|  |  +-- Filesystem                    |    |
|  |  |   +-- read_file                 |    |
|  |  |   +-- write_file                |    |
|  |  |   +-- edit_file                 |    |
|  |  |   +-- apply_patch               |    |
|  |  +-- Shell                         |    |
|  |      +-- run_command               |    |
|  |      +-- execute_script            |    |
|  |                                     |    |
|  |  MCPServer ---> host:8000          |    |
|  +-------------------------------------+    |
|                                              |
|  Workspace (/app):                           |
|  +-- project/README.md   (mounted)           |
|  +-- services/           (mounted)           |
|  +-- scratch/tasks.txt   (created)           |
+----------------------------------------------+
```

---

## 2. SandboxAgent Definition

### 2.1 Constructor Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `name` | `"Task Manager Sandbox"` | Human-readable agent name |
| `instructions` | See section 2.2 | System prompt with tool instructions |
| `mcp_servers` | `[MCPServer(url=...)]` | Connection to task-mcp server on host |
| `default_manifest` | See section 3 | Files available in sandbox workspace |
| `capabilities` | `[Filesystem(), Shell()]` | Sandbox-native tools |
| `model` | Default (gpt-4o) | OpenAI model - configurable via env |

### 2.2 Instructions (System Prompt)

```
You are a task management agent with filesystem and shell access.

You can:
1. Use MCP tools (capture_task, review_task, modify_task, resolve_task, remove_task)
2. Read and write files using Filesystem capability
3. Run shell commands using Shell capability

When a user asks you to create tasks from files:
  - Read the file using Filesystem
  - Extract task information
  - Call capture_task for each task found
  - Save a summary to scratch/tasks.txt
```

### 2.3 MCP Server Connection

| Property | Value |
|----------|-------|
| URL | `http://host.docker.internal:8000/mcp` |
| Transport | Streamable HTTP |
| Auto-discovered tools | `capture_task`, `review_task`, `modify_task`, `resolve_task`, `remove_task` |

The URL uses `host.docker.internal` because the SandboxAgent runs inside a Docker container and needs to reach the MCP server running on the host machine.

---

## 3. Manifest (Workspace Definition)

### 3.1 Entries

| Entry | Type | Source | Purpose |
|-------|------|--------|---------|
| `project/README.md` | `LocalDir` | `project_root/README.md` | Agent can read project-level docs |
| `services/` | `LocalDir` | `project_root/services/` | Agent can browse service code |
| `scratch/tasks.txt` | `StringEntry` | In-memory | Agent can write task summaries |

### 3.2 Entry Types (Available from SDK)

| Type | When to use |
|------|-------------|
| `LocalDir` | Mount a local directory into sandbox |
| `StringEntry` | Create a file with string content |
| `GitRepo` | Clone a git repository into sandbox |
| `S3Mount` | Mount S3 bucket (with mount strategy) |
| `GCSMount` | Mount GCS bucket |
| `R2Mount` | Mount Cloudflare R2 bucket |

---

## 4. Capabilities

### 4.1 Filesystem

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `read_file` | Read contents of a file | `path: str` | File content as text |
| `write_file` | Write content to a file | `path: str, content: str` | Confirmation |
| `edit_file` | Edit a file with search/replace | `path: str, old: str, new: str` | Confirmation |
| `apply_patch` | Apply a diff patch | `patch: str` | Confirmation |
| `list_directory` | List files in a directory | `path: str` | File list |

### 4.2 Shell

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `run_command` | Execute a shell command | `command: str` | stdout + stderr |
| `execute_script` | Run a script file | `path: str` | stdout + stderr |

### 4.3 Additional Capabilities (Future)

| Capability | Description | When to add |
|------------|-------------|-------------|
| `Skills` | Load workflow guides | When agent needs project-specific training |
| `Memory` | Persist learnings across sessions | When agent repeats mistakes |
| `Compaction` | Summarize long sessions | When context window fills up |

---

## 5. Sandbox Clients

### 5.1 Client Comparison

| Client | Install | Isolation | Use Case |
|--------|---------|-----------|----------|
| **UnixLocalSandboxClient** | None | None | Fast dev on macOS/Linux |
| **DockerSandboxClient** | `openai-agents[docker]` | Container | **Our choice** - K8s parity |
| E2BSandboxClient | `openai-agents[e2b]` | Remote | Production hosted |
| ModalSandboxClient | `openai-agents[modal]` | Remote | Production hosted |
| CloudflareSandboxClient | `openai-agents[cloudflare]` | Remote | Edge compute |

### 5.2 DockerSandboxClient Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| `client` | `DockerSandboxClient(docker_from_env())` | Uses local Docker daemon |
| `image` | `DEFAULT_PYTHON_SANDBOX_IMAGE` | SDK-managed Python image |
| `options` | `DockerSandboxClientOptions(...)` | Image override, mounts |

---

## 6. Dependencies

### 6.1 Python Packages

| Package | Version | Required for |
|---------|---------|--------------|
| `openai-agents[docker]` | >= 0.15.1 | SandboxAgent + Docker client |
| `docker` | latest | Docker SDK for Python |
| `python-dotenv` | >= 1.0.0 | Load OPENAI_API_KEY from .env |
| `openai` | >= 1.0.0 | OpenAI SDK (dep of openai-agents) |

### 6.2 System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | SandboxAgent requirement |
| Docker Desktop | Latest | For DockerSandboxClient |
| Docker daemon | Running | `docker ps` must succeed |
| OPENAI_API_KEY | Valid | Set in `.env` file |

---

## 7. CLI Usage

### 7.1 Installation

```bash
# From project root
uv sync

# Install Docker extra for SandboxAgent
uv sync --extra sandbox
```

### 7.2 Running

```bash
# Terminal 1: Start MCP server
cd services/task-mcp
uv run python -m task_manager_mcp
# -> http://localhost:8000/mcp

# Terminal 2: Run SandboxAgent
cd services/task-manager-agent
uv run python -m task_manager_agent.sandbox_agent "Read README.md and create a task"
```

### 7.3 Example Prompts

| Prompt | Expected Behavior |
|--------|-------------------|
| `"Read README.md and create a task"` | Agent reads file via Filesystem, calls `capture_task` |
| `"List all files in services/"` | Agent uses Filesystem to browse directory |
| `"Run ls -la in the workspace"` | Agent uses Shell to run command |
| `"Find all todos in the codebase"` | Agent uses Shell + Filesystem to search |
| `"Create tasks from all .md files"` | Agent reads multiple files, creates tasks via MCP |

---

## 8. Error Handling

### 8.1 Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| Docker not running | Daemon unavailable | Start Docker Desktop |
| `host.docker.internal` unreachable | MCP server not started | Start MCP server first |
| Sandbox creation timeout | Docker pulling image | Wait for image download |
| Permission denied | Filesystem read/write | Check manifest mount paths |

### 8.2 Cleanup

Sandbox sessions must be explicitly closed to free Docker resources:

```python
sandbox = await docker_client.create(...)
try:
    async with sandbox:
        # ... run agent
finally:
    await sandbox.close()  # Always cleanup
```

---

## 9. Integration with Simple Agent

### 9.1 Coexistence Pattern

```
Simple Agent (task manager CLI)
  +-- Handles: chat, MCP calls, task CRUD
  +-- When file/shell access needed:
        +-- Spawns SandboxAgent (sandboxed Docker container)
              +-- Reads files via Filesystem
              +-- Runs commands via Shell
              +-- Calls back to MCP tools for task storage
```

### 9.2 When to Use Which

| Task | Agent |
|------|-------|
| "Create a task: Buy groceries" | Simple Agent |
| "List all high priority tasks" | Simple Agent |
| "Read this file and create tasks from it" | **SandboxAgent** |
| "Run tests and report results as tasks" | **SandboxAgent** |
| "Find todos in my codebase" | **SandboxAgent** |
| "Edit my Dockerfile and capture the change" | **SandboxAgent** |

---

## 10. Future Evolution

### Phase 1: CLI SandboxAgent (Now)
- [x] DockerSandboxClient with Filesystem + Shell
- [x] MCP server connection via host.docker.internal
- [x] Manifest with LocalDir + StringEntry
- [ ] Test end-to-end

### Phase 2: Enhanced Capabilities
- [ ] Add Skills capability for guided workflows
- [ ] Add Memory capability for cross-session learning
- [ ] Add Compaction for long-running sessions
- [ ] Add GitRepo entries to manifest

### Phase 3: Session Persistence
- [ ] Save sandbox snapshots
- [ ] Resume sessions across runs
- [ ] Archive and restore workspace state

### Phase 4: Production
- [ ] Replace host.docker.internal with service mesh / internal DNS
- [ ] Add auth between SandboxAgent and MCP server
- [ ] Switch to hosted sandbox client (Modal, E2B) for scaling
- [ ] Deploy as K8s sidecar alongside Simple Agent

---

## 11. References

- [OpenAI Agents SDK: Agents](https://openai.github.io/openai-agents-python/agents/)
- [OpenAI Agents SDK: Sandbox Agents Quickstart](https://openai.github.io/openai-agents-python/sandbox_agents/)
- [OpenAI Agents SDK: Sandbox Clients](https://openai.github.io/openai-agents-python/sandbox/clients/)
- [OpenAI Agents SDK: MCP Integration](https://openai.github.io/openai-agents-python/mcp/)
- [Docker Sandbox Example](https://github.com/openai/openai-agents-python/blob/main/examples/sandbox/docker/docker_runner.py)
- [ADR-001: Agent Decision](docs/adrs/agent-decision.md)
- [MCP Evolution Phases](spec/mcp/roadmap/evolution-phases.md)
- [MCP Launch Spec](spec/mcp/implementation/launch-spec.md)
