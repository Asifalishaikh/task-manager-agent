"""
SandboxAgent — Task Manager Agent with Docker sandbox + MCP tools.

Runs inside a Docker container with:
  - MCP tools (capture, review, modify, resolve, remove tasks)
  - Gemini 3.1 Flash-Lite model via LiteLLM
  - Persistent workspace with Manifest files
  - OpenAI for tracing only (optional)

Note: Sandbox built-in capabilities (Filesystem, Shell) require OpenAI Responses API.
With Gemini (ChatCompletions), only MCP tools are available.

Usage:
  # Start MCP server first (Terminal 1):
  cd services/task-mcp && uv run python -m task_manager_mcp

  # Run SandboxAgent (Terminal 2):
  uv run python -m task_manager_agent.sandbox_agent "Create a task called 'My Task'"

Requirements:
  - Docker Desktop running
  - pip install openai-agents[docker]
  - GEMINI_API_KEY set in .env file (for agent calls)
  - OPENAI_API_KEY set in .env file (optional, for tracing only)
"""

import asyncio
import sys
import os
from pathlib import Path

from dotenv import load_dotenv
from docker import from_env as docker_from_env

from agents import Runner
from agents.run import RunConfig
from agents.mcp.server import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from agents.sandbox import SandboxAgent, SandboxRunConfig, Manifest
from agents.sandbox.entries import File
from agents.sandbox.sandboxes.docker import (
    DockerSandboxClient,
    DockerSandboxClientOptions,
)
from agents.sandbox.config import DEFAULT_PYTHON_SANDBOX_IMAGE
from agents.extensions.models.litellm_provider import LitellmProvider

load_dotenv()

# Use host.docker.internal so the container can reach the host's MCP server
MCP_SERVER_URL = "http://localhost:8000/mcp"

# Gemini model via LiteLLM (prefix with "gemini/")
MODEL_NAME = "gemini/gemini-3.1-flash-lite"


def build_manifest():
    """Build workspace manifest — files available inside the sandbox."""
    # sandbox_agent.py is at: services/task-manager-agent/src/task_manager_agent/sandbox_agent.py
    # project root is 4 levels up
    project_root = Path(__file__).resolve().parents[4]

    return Manifest(
        entries={
            "workspace/README.md": File(
                content=b"# Sandbox Workspace\n\nThis is the Task Manager Sandbox.\n"
            ),
            "scratch/tasks.txt": File(
                content=b"# Tasks extracted from files\n"
            ),
        }
    )


def build_mcp_server():
    """Create and connect MCP server."""
    return MCPServerStreamableHttp(
        params=MCPServerStreamableHttpParams(url=MCP_SERVER_URL)
    )


def build_agent(manifest, mcp_server):
    """Build the SandboxAgent with MCP tools + capabilities."""
    return SandboxAgent(
        name="Task Manager Sandbox",
        instructions=(
            "You are a task management agent.\n\n"
            "You can:\n"
            "1. Use MCP tools (capture_task, review_task, modify_task, resolve_task, remove_task)\n\n"
            "When a user asks you to create tasks:\n"
            "  - Use capture_task to create the task\n"
            "  - Reply with the task details\n"
        ),
        mcp_servers=[mcp_server],
        default_manifest=manifest,
        capabilities=[],  # No sandbox capabilities (Gemini uses ChatCompletions, not Responses API)
        model=MODEL_NAME,
    )


async def main():
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not found. Create a .env file with GEMINI_API_KEY=your-key")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: uv run python -m task_manager_agent.sandbox_agent <prompt>")
        print('Example: uv run python -m task_manager_agent.sandbox_agent "Read README.md and create a task"')
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])

    print("\n=== SandboxAgent ===")
    print(f"Model: {MODEL_NAME}")
    if os.getenv("OPENAI_API_KEY"):
        print("Tracing: OpenAI (enabled)")
    else:
        print("Tracing: disabled (no OPENAI_API_KEY)")
    print(f"Prompt: {prompt}\n")

    # Build manifest
    manifest = build_manifest()

    # Create and connect MCP server
    mcp_server = build_mcp_server()
    print("Connecting to MCP server...")
    await mcp_server.connect()
    print("MCP connected!")

    # Build agent with connected MCP server
    agent = build_agent(manifest, mcp_server)

    # Create Docker sandbox client
    docker_client = DockerSandboxClient(docker_from_env())

    # Create sandbox session
    sandbox = await docker_client.create(
        manifest=manifest,
        options=DockerSandboxClientOptions(
            image=DEFAULT_PYTHON_SANDBOX_IMAGE,
        ),
    )

    async with sandbox:
        result = await Runner.run(
            agent,
            prompt,
            max_turns=30,
            run_config=RunConfig(
                sandbox=SandboxRunConfig(session=sandbox),
                model_provider=LitellmProvider(),
                workflow_name="Sandbox Agent",
            ),
        )
        print("\n=== Result ===")
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
