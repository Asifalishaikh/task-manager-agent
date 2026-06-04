"""
Step 2: Test MCP connection — Simple Agent with MCP tools via Gemini
Run: uv run python -m task_manager_agent.test_mcp

Prerequisite: MCP server must be running in another terminal:
  cd services/task-mcp && uv run python -m task_manager_mcp
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from agents import Agent, Runner
from agents.mcp.server import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from agents.run import RunConfig
from agents.extensions.models.litellm_provider import LitellmProvider

MODEL_NAME = "gemini/gemini-3.1-flash-lite"
MCP_SERVER_URL = "http://localhost:8000/mcp"

async def main():
    print("=== Step 2: Test MCP Connection ===\n")

    if not os.getenv("GEMINI_API_KEY"):
        print("[ERROR] GEMINI_API_KEY not found in .env file")
        return

    mcp_server = MCPServerStreamableHttp(
        params=MCPServerStreamableHttpParams(url=MCP_SERVER_URL)
    )
    print(f"MCP Server: {MCP_SERVER_URL}")
    print("Connecting to MCP server...")
    await mcp_server.connect()
    print("Connected!")

    agent = Agent(
        name="TaskManager",
        instructions="You are a task manager. Use the available MCP tools to manage tasks. Keep responses short.",
        model=MODEL_NAME,
        mcp_servers=[mcp_server],
    )

    # Test 1: List tools
    print("\n--- Test 1: Ask agent to list available tools ---")
    result1 = await Runner.run(
        agent,
        "What MCP tools do you have available? List them briefly.",
        run_config=RunConfig(
            model_provider=LitellmProvider(),
            workflow_name="MCP Test - List Tools",
        ),
    )
    print(f"Result: {result1.final_output}")

    # Test 2: Create a task
    print("\n--- Test 2: Create a task ---")
    result2 = await Runner.run(
        agent,
        'Create a task called "Test task from Gemini" with high priority.',
        run_config=RunConfig(
            model_provider=LitellmProvider(),
            workflow_name="MCP Test - Create Task",
        ),
    )
    print(f"Result: {result2.final_output}")

    # Test 3: Review tasks
    print("\n--- Test 3: Review all tasks ---")
    result3 = await Runner.run(
        agent,
        "List all current tasks.",
        run_config=RunConfig(
            model_provider=LitellmProvider(),
            workflow_name="MCP Test - Review Tasks",
        ),
    )
    print(f"Result: {result3.final_output}")

    print("\n[OK] Step 2 complete - MCP connection tested!")

if __name__ == "__main__":
    asyncio.run(main())
