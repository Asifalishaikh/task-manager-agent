# ADR-001: Agent Selection — Simple Agent vs SandboxAgent

**Status:** Accepted (May 2026)
**Context:** OpenAI Agents SDK v1.x (harness introduced April 2026)

---

## Decision

Use **`Agent` (Simple Agent)** for the Task Manager Agent now, and adopt **`SandboxAgent`** with `DockerSandboxClient` when Kubernetes deployment requires workspace isolation.

---

## Options Considered

### Option 1: Simple Agent (`Agent`)

The core building block — an LLM configured with instructions, tools, MCP servers, handoffs, guardrails, and structured outputs.

```python
from agents import Agent, MCPServer

agent = Agent(
    name="Task Manager",
    instructions="You manage tasks using MCP tools.",
    mcp_servers=[MCPServer(url="http://localhost:8000/mcp")]
)
```

**Pros:**
- Minimal dependencies (`pip install openai-agents`)
- No sandbox client required
- Works on all OS
- Auto-discovers MCP tools
- Same API as SandboxAgent for tools, handoffs, guardrails

**Cons:**
- No filesystem access
- No shell command execution
- No persistent workspace

### Option 2: SandboxAgent

Extends `Agent` with workspace isolation, filesystem access, shell commands, skills, memory, and session snapshots.

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

**Pros:**
- All capabilities of Simple Agent
- Filesystem editing via `Filesystem` capability
- Shell execution via `Shell` capability
- Persistent workspace with `Manifest`
- Session snapshots for resume
- `DockerSandboxClient` provides container isolation → maps to K8s

**Cons:**
- **Beta feature** — API may change
- Requires sandbox client (`UnixLocalSandboxClient`, `DockerSandboxClient`, or hosted)
- Docker install needed for `DockerSandboxClient`
- Overhead for simple API-calling agents

---

## SandboxAgent Architecture (Deep Dive)

### 3 Sandbox Clients

| Client | Install | Isolation | Best for |
|--------|---------|-----------|----------|
| **`UnixLocalSandboxClient`** | None | None — runs on host | Fastest local dev (macOS/Linux) |
| **`DockerSandboxClient`** | `openai-agents[docker]` | Container isolation | **K8s parity**, CI/CD, repeatable builds |
| **Hosted clients** (E2B, Modal, Cloudflare, etc.) | Provider-specific | Full remote isolation | Production at scale |

### 5 Capabilities

| Capability | What it gives the agent | Our project use case |
|------------|------------------------|---------------------|
| **`Filesystem`** | Read, write, edit files, apply patches, list directories | Read task configs, edit project files, create artifacts |
| **`Shell`** | Run shell commands, execute scripts | Run tests, deploy, query system |
| **`Skills`** | Load guides that teach the agent workflows | Teach agent project-specific patterns |
| **`Memory`** | Persist learnings across sessions | Agent remembers past mistakes |
| **`Compaction`** | Summarize long sessions to save context | Keep context window from overflowing |

### Manifest System (Workspace Definition)

```python
Manifest(entries={
    "repo": LocalDir(src="/path/to/repo"),       # Mount local directory
    "task-list": StringEntry("[]"),               # Create in-memory file
    "data": GitRepo(url="...", ref="main"),       # Clone a git repo
    "models": S3Mount(bucket="my-bucket"),        # Cloud storage mount
})
```

### Architecture with MCP Server

```
User Request
      │
      ▼
Simple Agent (Task Manager)        ← handles chat + MCP tool calls
      │
      ├── calls MCP tools ────► MCP Server (:8000)
      │                              │
      │                              ▼
      │                        InMemoryTaskStore
      │
      └── spawns SandboxAgent ──► DockerSandboxClient
                                       │
                                       ▼
                                Docker Container
                                  ├── Filesystem (edit files)
                                  ├── Shell (run commands)
                                  └── MCP tools also available
```

### How SandboxAgent Benefits This Project

| Scenario | Without SandboxAgent | With SandboxAgent |
|----------|---------------------|-------------------|
| "Create a task from this file" | Can't read file ❌ | Reads file via `Filesystem`, calls `capture_task` ✅ |
| "Run tests for my project" | Can't run commands ❌ | Runs tests via `Shell`, reports results ✅ |
| "Summarize my logs" | Can't access logs ❌ | Reads logs via `Filesystem`, summarizes ✅ |
| "Fix this bug in the repo" | Can't edit code ❌ | Edits via `Filesystem`, tests via `Shell` ✅ |

---

## Decision Drivers

| Driver | Weight | Winning Option |
|--------|--------|---------------|
| Time to working agent | High | Simple Agent (zero config) |
| MCP tool integration | High | Both (identical MCP support) |
| K8s readiness | Medium | SandboxAgent (Docker client) |
| Development speed | High | Simple Agent (no sandbox setup) |
| Future extensibility | Medium | SandboxAgent (capabilities) |

---

## Consequences

### Positive
- Can build and test the agent immediately with no additional setup
- SandboxAgent exploration can happen in parallel later
- Both agents share the same MCP, tools, handoffs, and guardrails API
- Migration path is clear: adopt `SandboxAgent` when file/shell access is needed
- DockerSandboxClient provides container isolation → natural bridge to K8s

### Negative
- Will need to refactor if switching from Simple Agent to SandboxAgent
- SandboxAgent requires Docker installed for container-backed sandboxes

### Neutral
- SandboxAgent is in beta — API may stabilize over time
- Both agent types can coexist: Simple for chat, SandboxAgent for file operations

---

## Implementation Plan

### Phase 1: Simple Agent (Now)
1. Create `services/task-manager-agent/src/agent.py` with `Agent` + `MCPServer`
2. Create CLI runner in `main.py`
3. Test end-to-end: terminal → agent → MCP tools

### Phase 2: SandboxAgent + DockerSandboxClient (Next)
1. Install `openai-agents[docker]`
2. Create a `sandbox_agent.py` with `Filesystem` + `Shell` capabilities
3. Set up `DockerSandboxClient` with a Python sandbox image
4. Connect SandboxAgent to MCP tools alongside Simple Agent
5. Test: "Read this file and create a task from it"
6. Test snapshot/session resume

### Phase 3: Kubernetes (Future)
1. Deploy Simple Agent as HTTP service in K8s pod
2. Add SandboxAgent as sidecar for file/code operations
3. Use `DockerSandboxClient` for container-level isolation
4. Add hosted sandbox client for production scaling

---

## References

- [OpenAI Agents SDK: Agents](https://openai.github.io/openai-agents-python/agents/)
- [OpenAI Agents SDK: Sandbox Agents Quickstart](https://openai.github.io/openai-agents-python/sandbox_agents/)
- [OpenAI Agents SDK: Sandbox Clients](https://openai.github.io/openai-agents-python/sandbox/clients/)
- [OpenAI Agents SDK: MCP Integration](https://openai.github.io/openai-agents-python/mcp/)
- [Docker Sandbox Example](https://github.com/openai/openai-agents-python/blob/main/examples/sandbox/docker/docker_runner.py)
- `spec/mcp/roadmap/evolution-phases.md`
- `README.md` — Agent Types section
