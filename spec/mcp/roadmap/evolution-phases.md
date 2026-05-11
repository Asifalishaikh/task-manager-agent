# MCP Server - Evolution Phases

> **Purpose:** Track future upgrades. Current implementation is in-memory, flat tasks, no auth.
> Each phase is backwards-compatible. Tools never change - only the underlying layers evolve.

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

## Phase 5 - Kubernetes Deployment

Production deployment target:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: task-mcp-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: task-mcp-server
  template:
    spec:
      containers:
      - name: mcp-server
        image: task-mcp-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: MCP_API_KEY
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: api-key
        - name: DATABASE_URL
          value: "postgresql://..."
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
```

## Summary

```
Now      -> In-memory, flat tasks, no auth
Phase 2  -> + Database (SQLite -> PostgreSQL)
Phase 3  -> + User concept (owner field, scoped queries)
Phase 4  -> + Auth enforcement (API keys / JWT)
Phase 5  -> + K8s deployment (scaling, secrets, probes)
```
