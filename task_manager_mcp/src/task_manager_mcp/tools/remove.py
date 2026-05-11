from ..models import RemoveTaskInput
from ..server import mcp, store


@mcp.tool(
    name="remove_task",
    annotations={
        "title": "Remove a Task",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def remove_task(input: RemoveTaskInput) -> str:
    """Delete a task entirely. This is discarding, not completing."""
    try:
        task = store.get(input.task_id)
        if task is None:
            return f"Error: Task not found: {input.task_id}"

        title = task.title
        store.delete(input.task_id)
        msg = f"**Task Removed**\n\n- **ID:** `{input.task_id}`\n- **Title:** {title}\n"
        if input.reason:
            msg += f"- **Reason:** {input.reason}\n"
        return msg
    except Exception as e:
        return f"Error: Failed to remove task - {e}"
