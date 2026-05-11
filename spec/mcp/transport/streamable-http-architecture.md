# Streamable HTTP Transport - Multi-Agent MCP Architecture

> **Status:** Decided
> **Date:** 2026-05-08
> **Context:** MCP server must serve multiple heterogeneous AI agents concurrently.
> **Decision:** Use **Streamable HTTP** transport over stdio.

---

## 1. Why Streamable HTTP (not stdio)

stdio runs the MCP server as a subprocess of the client - one per agent, local only.
Streamable HTTP runs it as a network service - all agents share one instance.

| | stdio | Streamable HTTP |
|---|---|---|
| **Scope** | Local machine | Remote accessible |
| **Clients** | One per process | Multiple concurrent |
| **Deployment** | Subprocess | Web service |
| **State sharing** | No (each isolated) | Yes (single shared store) |

---

## 2. Architecture

```
Agent A ---+
Agent B ---+-- HTTP POST /mcp --> FastMCP Server --> TaskStore (in-memory)
Agent C ---+    (JSON-RPC 2.0)
```

Each agent sends JSON-RPC requests to a single endpoint:
```
POST /mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "capture_task",
    "arguments": { "title": "Review the PR" }
  }
}
```

---

## 3. Implementation

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("task_manager_mcp")

# ... tool definitions ...

if __name__ == "__main__":
    mcp.run(transport="streamable_http", port=8000)
```

---

## 4. Current Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Transport | Streamable HTTP | Multi-agent, remote |
| Framework | FastMCP (Python) | Python project |
| Auth | None (skip now) | Single-tenant, in-memory |
| User concept | None (skip now) | Flat tasks, no identity |
| Storage | In-memory | Zero setup, fast iteration |
| State model | Stateless | Scales horizontally |

---

## 5. References

- MCP Specification: https://modelcontextprotocol.io/specification/draft.md
- FastMCP Python SDK: https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md
- MCP Best Practices: (skill reference)
- Future Phases: `spec/mcp/roadmap/evolution-phases.md`
