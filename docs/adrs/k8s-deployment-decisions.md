# ADR-002: K8s Deployment Decisions — Docker Desktop Development

**Status:** Accepted (June 2026)
**Context:** Deploying MCP Server + SandboxAgent to Docker Desktop K8s for local development and testing.

---

## Decision Summary

| # | Decision | Choice |
|---|----------|--------|
| 1 | ServiceAccount / RBAC | Not needed — remove from manifests |
| 2 | Pod security | `securityContext` at pod + container level |
| 3 | SandboxAgent runtime | `command: ["sleep", "infinity"]` — keep pod alive for exec |
| 4 | Secrets | Base64-encoded from `.env`, never committed |
| 5 | MCP replicas | 2 (basic availability) |
| 6 | CI → K8s | Manual `kubectl apply` after CI pushes image |

---

## Decision 1: No Dedicated ServiceAccount

### Context
K8s best practices say to create a dedicated ServiceAccount with least-privilege RBAC instead of using the `default` SA.

### Decision
Remove `serviceAccountName: default` from both deployment manifests entirely. When omitted, K8s assigns the default SA implicitly — same behavior.

### Rationale
RBAC only matters when a pod interacts with the K8s API (get pods, list services, create resources, etc.). Our services:
- MCP Server: receives MCP calls, queries in-memory store, returns responses
- SandboxAgent: receives prompts, calls MCP tools via DNS, uses Docker socket
- Future services: same pattern — HTTP/MCP, never K8s API calls

All inter-service communication uses DNS (`task-mcp-service.task-manager.svc.cluster.local`) or MCP protocol. RBAC is unnecessary until a pod needs K8s API access.

### Consequences
- Less code to maintain
- Identical behavior (K8s uses default SA implicitly)
- If a future service needs K8s API access, we create SA + RBAC at that point

---

## Decision 2: securityContext Enforcement

### Context
The Dockerfile creates a non-root user (`USER app`, uid 1001). Without K8s-level enforcement, any change to the Dockerfile could accidentally run as root.

### Decision
Two levels of securityContext:

**Pod-level (both deployments):**
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
```

**Container-level (SandboxAgent only — has Docker socket):**
```yaml
securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
```

### Rationale
- `runAsNonRoot: true` — K8s refuses to start the pod if the container runs as root. Defense against accidental Dockerfile changes.
- `allowPrivilegeEscalation: false` — Prevents sudo/setuid inside the container. Critical because SandboxAgent mounts `/var/run/docker.sock` — a compromised container with privilege escalation could control the host Docker daemon.
- `drop: ["ALL"]` — Removes all Linux capabilities. Reduces kernel attack surface.

### Non-decisions
- `readOnlyRootFilesystem: true` — NOT applied. Would break agents that write temp files/cache.
- `runAsGroup` / `fsGroup` — NOT needed. Pods don't write to shared volumes.

### Consequences
- Docker socket is owned by `root:root` on host. uid 1001 may have permission errors when SandboxAgent tries Docker-in-Docker operations.
- If Docker sandbox fails, options: (a) run container as root (bad), (b) add uid 1001 to docker group, (c) fall back to Simple Agent (non-sandboxed).

### Lesson: Pod-level vs Container-level fields
`allowPrivilegeEscalation` and `capabilities` are **container-level** fields, not pod-level. Putting them under `spec.securityContext` causes:
```
strict decoding error: unknown field "spec.template.spec.securityContext.allowPrivilegeEscalation"
```

---

## Decision 3: sleep infinity for SandboxAgent

### Context
SandboxAgent is a CLI tool — it takes a prompt as argument, processes it, then exits. It has no HTTP server, no event loop. A standard Deployment would restart it in a loop.

### Decision
Override the Dockerfile ENTRYPOINT with `command: ["sleep", "infinity"]`.

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **sleep infinity** (chosen) | Simple, pod stays alive for exec, easy debugging | Agent never runs automatically |
| **K8s Job** | Runs once per prompt, terminates cleanly | Need trigger mechanism, overkill for dev |
| **HTTP wrapper** | Agent triggered via endpoint | Requires refactoring, extra surface |
| **Sidecar pattern** | Agent responds to events | Premature for dev phase |

### Rationale
For development and testing, `sleep infinity` is the simplest approach. We interact with the agent by `kubectl exec` into the pod manually. Revisit when the agent needs to respond to events automatically.

### Consequences
- All agent interactions are manual (`kubectl exec`)
- No auto-recovery if the agent process exits
- Pod stays alive, consuming resources

---

## Decision 4: Base64 Secrets from .env

### Context
API keys (GEMINI_API_KEY, OPENAI_API_KEY) must reach pods securely without touching GitHub.

### Decision
Use `kubectl create secret generic --from-env-file=.env` to generate a local `secret.yaml`, then `kubectl apply` it. The file is in `.gitignore`.

### Rationale
- `.env` stays local (never pushed)
- `secret.yaml` is generated locally, applied locally (never pushed)
- Only the K8s cluster stores the encoded secrets in its encrypted etcd
- For production, replace with Sealed Secrets or External Secrets Operator

### Important: Base64 is NOT encryption
```bash
echo "QVEuQWI4Uk42SzVv..." | base64 -d
# → instantly shows the real API key
```
The security chain relies on `.gitignore` + K8s etcd encryption, not base64.

### Lesson: .env file format matters
Each line must be exactly `KEY=VALUE` on a single line. A newline in the middle of a value creates a malformed YAML complex key:
```yaml
? sk-proj-DZ5v...     # malformed
: ""                  # empty value
```
Always verify `secret.yaml` after generation.

---

## Decision 5: MCP Server Replicas

### Context
Production K8s typically runs 2+ replicas for high availability.

### Decision
Set `replicas: 2` for MCP server (HTTP service). SandboxAgent stays at 1 (CLI tool, no incoming traffic).

### Rationale
- Docker Desktop is a single-node cluster — true HA isn't possible
- 2 replicas provides basic redundancy if one pod restarts
- SandboxAgent doesn't serve requests — no benefit from multiple replicas

### Consequences
- Both MCP pods are identical and serve independently
- Service (ClusterIP) load-balances between them
- If one crashes, the other still responds

---

## Decision 6: CI + Registry, Manual K8s Deploy

### Context
Full CD would auto-deploy to K8s after every CI build. This is the typical end state.

### Decision
Keep CI and K8s deploy separate for now:
- CI: build + push to ghcr.io (automatic on push)
- K8s: manual `kubectl apply` after CI completes

### Rationale
- Docker Desktop K8s is a dev environment — no need for auto-deploy
- Manual deploy gives control over when updates roll out
- Full CD will be added when deploying to a cloud K8s cluster

### Future
```yaml
# GitHub Actions step (not yet implemented)
- name: Deploy to K8s
  run: kubectl apply -f Deployments/k8s/
```

---

## References
- `Deployments/k8s/` — manifest files
- `docs/developer-notes/k8s-deployment-scenarios.md` — complete command reference
- `docs/PROJECT_JOURNEY.txt` — Part 3: K8s journey and fixes
- `K8s securityContext docs` — https://kubernetes.io/docs/tasks/configure-pod-container/security-context/
- `K8s ServiceAccount docs` — https://kubernetes.io/docs/concepts/security/service-accounts/
