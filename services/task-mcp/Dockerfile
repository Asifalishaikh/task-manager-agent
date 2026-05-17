# =============================================================================
# Task Manager MCP Server — Multi-Stage Dockerfile
#
# Build:
#   docker build -t task-mcp:latest -f services/task-mcp/Dockerfile services/task-mcp
#
# Run:
#   docker run -d --name task-mcp -p 8000:8000 task-mcp:latest
#
# Verify:
#   curl -X POST http://localhost:8000/mcp \
#     -H "Content-Type: application/json" \
#     -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
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
COPY pyproject.toml README.md ./
RUN uv lock && \
    uv sync --no-dev --no-install-project && \
    uv export --no-dev --format=requirements-txt > requirements.txt

# ── Layer 2: Source code (changes frequently) ─────────────────────────
COPY src/ ./src/
RUN uv sync --no-dev && \
    python -c "from task_manager_mcp.server import mcp; tools = mcp._tool_manager.tools; print(f'Verified {len(tools)} tools registered')"

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

EXPOSE 8000

USER app

# Health check — verifies the server is accepting connections
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('localhost',8000),timeout=5); s.close()"

# Start the MCP server with Streamable HTTP transport
ENTRYPOINT ["python", "-m", "task_manager_mcp"]
