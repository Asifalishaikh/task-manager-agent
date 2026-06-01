"""
SandboxAgent — Task Manager Agent with filesystem + shell capabilities.

Runs inside a Docker container with:
  - Filesystem access (read, write, edit files)
  - Shell access (run commands, execute scripts)
  - MCP tools (capture, review, modify, resolve, remove tasks)
  - Gemini 3.1 Flash-Lite model via LiteLLM
  - OpenAI for tracing only (optional)

Usage:
  # Start MCP server first (Terminal 1):
  cd services/task-mcp && uv run python -m task_manager_mcp

  # Run SandboxAgent (Terminal 2):
  uv run python -m task_manager_agent.sandbox_agent "Create a task from README.md"

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

from agents import MCPServer, Runner
from agents.run import RunConfig
from agents.sandbox import SandboxAgent, SandboxRunConfig, Manifest
from agents.sandbox.entries import LocalDir, StringEntry
from agents.sandbox.capabilities import Capabilities
from agents.sandbox.sandboxes.docker import (
    DockerSandboxClient,
    DockerSandboxClientOptions,
)
from agents.sandbox.config import DEFAULT_PYTHON_SANDBOX_IMAGE
from agents.extensions.models.litellm_provider import LitellmProvider

load_dotenv()

# Use host.docker.internal so the container can reach the host's MCP server
MCP_SERVER_URL = "http://host.docker.internal:8000/mcp"

# Gemini model via LiteLLM (prefix with "gemini/")
MODEL_NAME = "gemini/gemini-3.1-flash-lite"


def build_manifest():
    """Build workspace manifest — files available inside the sandbox."""
    project_root = Path(__file__).resolve().parents[3]  # task-manager-agent root

    return Manifest(
        entries={
            "project/README.md": LocalDir(
                src=str(project_root / "README.md")
            ),
            "scratch/tasks.txt": StringEntry(
                content="# Tasks extracted from files\n"
            ),
            "services": LocalDir(src=str(project_root / "services")),
        }
    )


def build_agent(manifest):
    """Build the SandboxAgent with MCP tools + capabilities."""
    mcp_server = MCPServer(url=MCP_SERVER_URL)

    return SandboxAgent(
        name="Task Manager Sandbox",
        instructions=(
            "You are a task management agent with filesystem and shell access.\n\n"
            "You can:\n"
            "1. Use MCP tools (capture_task, review_task, modify_task, resolve_task, remove_task)\n"
            "2. Read and write files using Filesystem capability\n"
            "3. Run shell commands using Shell capability\n\n"
            "When a user asks you to create tasks from files:\n"
            "  - Read the file using Filesystem\n"
            "  - Extract task information\n"
            "  - Call capture_task for each task found\n"
            "  - Save a summary to scratch/tasks.txt\n"
        ),
        mcp_servers=[mcp_server],
        default_manifest=manifest,
        capabilities=Capabilities.default(),  # Filesystem + Shell + Compaction
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

    # Build manifest + agent
    manifest = build_manifest()
    agent = build_agent(manifest)

    # Create Docker sandbox client
    docker_client = DockerSandboxClient(docker_from_env())

    # Create sandbox session
    sandbox = await docker_client.create(
        manifest=manifest,
        options=DockerSandboxClientOptions(
            image=DEFAULT_PYTHON_SANDBOX_IMAGE,
        ),
    )

    try:
        async with sandbox:
            result = await Runner.run(
                agent,
                prompt,
                run_config=RunConfig(
                    sandbox=SandboxRunConfig(session=sandbox),
                    model_provider=LitellmProvider(),
                    workflow_name="Sandbox Agent",
                ),
            )
            print("\n=== Result ===")
            print(result.final_output)
    finally:
        await sandbox.close()


if __name__ == "__main__":
    asyncio.run(main())
