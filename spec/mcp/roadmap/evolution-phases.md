# MCP Server - Evolution Phases

> **Purpose:** Track future upgrades. Current implementation is in-memory, flat tasks, no auth.
> Each phase is backwards-compatible. Tools never change - only the underlying layers evolve.

---

## ✅ Phase 1 — Foundation (Complete)

### 1a. MCP Server (5 Intent-Based Tools)
- FastMCP server with Streamable HTTP transport on port 8000
- 5 tools: `capture_task`, `review_task`, `modify_task`, `resolve_task`, `remove_task`
- In-memory thread-safe task store (`InMemoryTaskStore`)
- Pydantic models with validation and Field constraints
- Markdown response format for agent-friendly output
- Remote MCP client config (`.mcp.json`)

### 1b. Multi-Stage Docker Build
- Builder stage: uv dependency installation, bytecode compilation, tool verification
- Runtime stage: minimal Python 3.12-slim, non-root user, HEALTHCHECK
- Image: `ghcr.io/asifalishaikh/task-manager-agent/task-manager-mcp`

### 1c. CI + Registry (GitHub Actions)
Two path-filtered workflows:

| Service | Workflow | Trigger Path | Image |
|---------|----------|-------------|-------|
| MCP Server | `task-mcp-build.yml` | `services/task-mcp/**` | `ghcr.io/.../task-manager-mcp` |
| SandboxAgent | `task-agent-build.yml` | `services/task-manager-agent/**` | `ghcr.io/.../task-sandbox-agent` |

Auto-builds and pushes to ghcr.io on every master push (CI + delivery only).
Full CD (auto-deploy to K8s) will be added in Phase 5.
- Tags: commit SHA, branch name, semver releases

### 1d. Agent SDK Research & Testing
- Studied `Agent` (Simple) vs `SandboxAgent` — documented in ADR-001
- Simple Agent tested with Gemini 3.1 Flash-Lite + MCP tools ✅
- SandboxAgent tested with DockerSandboxClient + MCP tools ✅
- Key finding: Sandbox Filesystem/Shell capabilities require OpenAI Responses API

---

## Phase 2 - Database Persistence

When in-memory storage needs persistence:

- Swap `InMemoryTaskStore` with `DatabaseTaskStore` (same interface)
- Start with **SQLite** (zero setup, file-based)
- Migrate to **PostgreSQL** for K8s production
- Tool interfaces stay identical - no agent-facing changes

## Phase 3 - User Concept

When we need task ownership/scoping:

- Add `owner: str = "default"` to Task model
- `capture_task` auto-assigns owner from request context
- `review_task` scopes results by owner
- Still no auth enforcement - owner is a trust-based string

## Phase 4 - Login & Auth

When auth enforcement is required:

```
Request -> Auth Middleware -> Tool Handler
                 |
           Reject if invalid
```

Options:
- **API Keys** - Simple, env-based. Map key to user identity.
- **JWT** - Standard for K8s. Validate via public key.
- **OAuth 2.1** - External/multi-team access.

Auth middleware extracts user identity and injects into request context.
Tools never handle auth directly.

## ✅ Phase 5 - Kubernetes Deployment (Complete)

Both services deployed to Docker Desktop K8s. Local dev cluster for testing.

### 5a. Secrets from .env (Step-by-Step)

API keys never touch GitHub. Flow:

```bash
# 1. Generate secret.yaml from local .env (encodes to base64 automatically)
kubectl create secret generic task-sandbox-secret \
  --from-env-file=.env \
  --namespace=task-manager \
  --dry-run=client -o yaml > secret.yaml

# 2. Add to .gitignore (never commit)
echo "secret.yaml" >> .gitignore

# 3. Apply to cluster
kubectl apply -f secret.yaml

# 4. Reference in deployment.yaml:
# env:
#   - name: GEMINI_API_KEY
#     valueFrom:
#       secretKeyRef:
#         name: task-sandbox-secret
#         key: GEMINI_API_KEY
```

### 5b. Deployed Services

| Service | Replicas | Type | Access |
|---------|----------|------|--------|
| task-mcp | 2 | HTTP Server (:8000) | `task-mcp-service.task-manager.svc.cluster.local` |
| task-sandbox-agent | 1 | CLI (sleep infinity) | kubectl exec |

### 5c. Security hardening applied
- Pod-level securityContext: `runAsNonRoot`, `runAsUser: 1001`
- Container-level: `allowPrivilegeEscalation: false`, `capabilities.drop: ALL`
- serviceAccountName removed (default SA used implicitly)
- Secrets generated from .env, never committed to GitHub

### 5d. Known limitations
- Gemini free tier quota (429 errors) blocks LLM calls after heavy testing
- Docker socket owned by root — uid 1001 may have permission issues with DockerSandboxClient
- `sleep infinity` keeps agent alive but doesn't run it actively

## Summary

```
Phase 1  -> MCP Server + Docker + CI/CD + Agent SDK research & testing ✅
Phase 2  -> + Database (SQLite -> PostgreSQL)
Phase 3  -> + User concept (owner field, scoped queries)
Phase 4  -> + Auth enforcement (API keys / JWT)
Phase 5  -> + K8s deployment (Docker Desktop, securityContext, secrets) ✅
```
