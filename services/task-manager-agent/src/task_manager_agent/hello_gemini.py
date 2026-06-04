"""
Step 1: Hello World — Test Gemini model via LiteLLM
Run: uv run python -m task_manager_agent.hello_gemini
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from agents import Agent, Runner
from agents.run import RunConfig
from agents.extensions.models.litellm_provider import LitellmProvider

MODEL_NAME = "gemini/gemini-3.1-flash-lite"

async def main():
    print("=== Step 1: Hello Gemini ===")
    
    # Validate API key
    if not os.getenv("GEMINI_API_KEY"):
        print("[ERROR] GEMINI_API_KEY not found. Add it to .env file")
        return

    # Simple agent — no MCP, no sandbox, just talk
    agent = Agent(
        name="HelloGemini",
        instructions="You are a helpful assistant. Keep responses very short.",
        model=MODEL_NAME,
    )

    print(f"\nModel: {MODEL_NAME}")
    print("Prompt: Say hello in one sentence\n")

    result = await Runner.run(
        agent,
        "Say hello in one sentence",
        run_config=RunConfig(
            model_provider=LitellmProvider(),
            workflow_name="Hello Gemini",
        ),
    )

    print(f"Response: {result.final_output}")
    print("\n[OK] Step 1 complete - Gemini is working!")

if __name__ == "__main__":
    asyncio.run(main())
