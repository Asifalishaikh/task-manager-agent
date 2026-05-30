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
- Migration path is clear: swap `Agent` for `SandboxAgent` when needed

### Negative
- Will need to refactor when switching to SandboxAgent for K8s
- Two agent types to maintain until K8s deployment

### Neutral
- SandboxAgent is in beta — waiting gives time for API stabilization

---

## Implementation Plan

### Phase 1: Simple Agent (Now)
1. Create `services/task-manager-agent/src/agent.py` with `Agent` + `MCPServer`
2. Create CLI runner in `main.py`
3. Test end-to-end: terminal → agent → MCP tools

### Phase 2: SandboxAgent Exploration (After CLI)
1. Install `openai-agents[docker]`
2. Set up `DockerSandboxClient`
3. Build SandboxAgent with `Filesystem` + `Shell` capabilities
4. Connect to MCP tools alongside Simple Agent
5. Test snapshot/session resume

### Phase 3: Kubernetes (Future)
1. Deploy Simple Agent as an HTTP service in K8s pod
2. Add SandboxAgent as sidecar for file/code operations
3. Use `DockerSandboxClient` for container-level isolation

---

## References

- [OpenAI Agents SDK: Agents](https://openai.github.io/openai-agents-python/agents/)
- [OpenAI Agents SDK: Sandbox Agents Quickstart](https://openai.github.io/openai-agents-python/sandbox_agents/)
- [OpenAI Agents SDK: Sandbox Clients](https://openai.github.io/openai-agents-python/sandbox/clients/)
- [OpenAI Agents SDK: MCP Integration](https://openai.github.io/openai-agents-python/mcp/)
- `spec/mcp/roadmap/evolution-phases.md`
- `README.md` — Agent Types section
