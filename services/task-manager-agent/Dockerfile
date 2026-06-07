# =============================================================================
# Task Manager SandboxAgent — Multi-Stage Dockerfile
#
# This image runs the SandboxAgent, which:
#   - Connects to the MCP server for task CRUD operations
#   - Uses DockerSandboxClient for workspace isolation
#   - Requires Docker socket access at runtime
#
# Build:
#   docker build -t task-agent:latest -f services/task-manager-agent/Dockerfile services/task-manager-agent
#
# Run (MCP server must be running on host):
#   docker run --rm \
#     -v /var/run/docker.sock:/var/run/docker.sock \
#     -e GEMINI_API_KEY=your_key \
#     --network host \
#     task-agent:latest "Create a task called Test"
# =============================================================================

# ---------------------------------------------------------------------------
# STAGE 1 — Builder: install dependencies and build the project
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv — fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Configure uv for minimal output and no caches in final layer
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# ── Layer 1: Dependencies (changes infrequently) ──────────────────────
COPY pyproject.toml ./
RUN uv lock && \
    uv sync --no-dev --no-install-project --extra sandbox --extra litellm && \
    uv export --no-dev --format=requirements-txt > requirements.txt

# ── Layer 2: Source code (changes frequently) ─────────────────────────
COPY src/ ./src/
RUN uv sync --no-dev --extra sandbox --extra litellm && \
    uv run python -c "from task_manager_agent.sandbox_agent import build_agent, build_mcp_server, build_manifest; print('SandboxAgent modules verified OK')"

# ---------------------------------------------------------------------------
# STAGE 2 — Runtime: minimal image with only what is needed to run
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Create non-root user (security best practice)
RUN addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --ingroup app --no-create-home app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy application source code
COPY --from=builder --chown=app:app /app/src /app/src

# Environment configuration
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

# Start the SandboxAgent CLI (prompt passed as arguments)
ENTRYPOINT ["python", "-m", "task_manager_agent.sandbox_agent"]
