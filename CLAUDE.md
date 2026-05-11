# Project Instructions

## Available Skills

The following skills are installed in this project (see `.agents/skills/`):

### mcp-builder
- **Purpose:** Guide for creating MCP servers (Python FastMCP or TypeScript MCP SDK)
- **When activated:** Load `.agents/skills/mcp-builder/SKILL.md` and its reference files when starting MCP server development
- **References:**
  - `.agents/skills/mcp-builder/reference/mcp_best_practices.md`
  - `.agents/skills/mcp-builder/reference/python_mcp_server.md`
  - `.agents/skills/mcp-builder/reference/node_mcp_server.md`
  - `.agents/skills/mcp-builder/reference/evaluation.md`

## Note
Skills are NOT MCP servers. Skills are prompt guides that help the AI. MCP servers provide executable tools under `/mcp`. The `mcp-builder` skill teaches how to build MCP servers — it does not provide MCP tools itself.

## Architecture Specs

MCP architecture decisions are documented under `spec/mcp/`:
- `spec/mcp/transport/streamable-http-architecture.md` — Streamable HTTP transport for multi-agent deployment
- `spec/mcp/tools/human-intent-based-tools.md` — 5 intent-based tools (capture, review, modify, resolve, remove)
- `spec/mcp/implementation/plan.md` — Step-by-step build plan using uv
- `spec/mcp/roadmap/evolution-phases.md` — Future phases (DB, auth, K8s)

## Slash Commands

| Command | Description |
|---------|-------------|
| `/mcp-builder` | Launch the MCP Server Builder guide — 4-phase workflow for building MCP servers |
