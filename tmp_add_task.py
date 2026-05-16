import asyncio, sys
sys.path.insert(0, "D:/coding/task-manegment-agent/.agents/skills/mcp-builder/scripts")
from connections import create_connection

async def main():
    conn = create_connection(transport="http", url="http://localhost:8000/mcp")
    async with conn:
        result = await conn.call_tool("capture_task", {
            "input": {
                "title": "Open Claw project submission",
                "description": "Submit the Open Claw project by Monday 8pm",
                "priority": "high"
            }
        })
        print(result)

asyncio.run(main())
