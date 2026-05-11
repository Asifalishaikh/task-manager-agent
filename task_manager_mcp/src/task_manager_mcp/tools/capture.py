from ..models import CaptureTaskInput
from ..server import mcp, store


@mcp.tool(
    name="capture_task",
    annotations={
        "title": "Capture a Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def capture_task(input: CaptureTaskInput) -> str:
    """Store a task from natural language. The agent extracts what matters."""
    try:
        task = store.create(input.model_dump())
        return (
            "**Task Captured**\n\n"
            f"- **ID:** `{task.id}`\n"
            f"- **Title:** {task.title}\n"
            f"- **Priority:** {task.priority.value}\n"
            f"- **Status:** {task.status.value}\n"
            f"- **Created:** {task.created_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        )
    except Exception as e:
        return f"Error: Failed to capture task - {e}"
