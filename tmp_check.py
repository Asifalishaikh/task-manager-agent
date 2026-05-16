import asyncio, sys
sys.path.insert(0, "D:/coding/task-manegment-agent/.agents/skills/mcp-builder/scripts")
from connections import create_connection

async def main():
    conn = create_connection(transport="http", url="http://localhost:8000/mcp")
    async with conn:
        tools = await conn.list_tools()
        print("Tools:", [t["name"] for t in tools])
        result = await conn.call_tool("review_task", {"input": {}})
        print("Result:", result)

asyncio.run(main())

