from ..models import ModifyTaskInput
from ..server import mcp, store


@mcp.tool(
    name="modify_task",
    annotations={
        "title": "Modify a Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def modify_task(input: ModifyTaskInput) -> str:
    """Update any field(s) of an existing task. Partial update."""
    try:
        task = store.update(input.task_id, input.model_dump(exclude_none=True))
        tags_str = f" [{', '.join(task.tags)}]" if task.tags else ""
        return (
            "**Task Updated**\n\n"
            f"- **ID:** `{task.id}`\n"
            f"- **Title:** {task.title}\n"
            f"- **Status:** {task.status.value}\n"
            f"- **Priority:** {task.priority.value}\n"
            f"- **Assignee:** {task.assignee or 'unassigned'}\n"
            f"- **Tags:** {tags_str or 'none'}\n"
            f"- **Updated:** {task.updated_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        )
    except KeyError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: Failed to modify task - {e}"
