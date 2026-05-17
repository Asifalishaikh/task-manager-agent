from ..models import ResolveTaskInput
from ..server import mcp, store


@mcp.tool(
    name="resolve_task",
    annotations={
        "title": "Resolve a Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def resolve_task(input: ResolveTaskInput) -> str:
    """Mark a task as completed/resolved."""
    try:
        task = store.resolve(input.task_id, input.resolution_note)
        note = f"\n- **Note:** {input.resolution_note}" if input.resolution_note else ""
        return (
            "**Task Resolved**\n\n"
            f"- **ID:** `{task.id}`\n"
            f"- **Title:** {task.title}\n"
            f"- **Status:** {task.status.value}\n"
            f"- **Resolved At:** {task.resolved_at.strftime('%Y-%m-%d %H:%M UTC')}"
            f"{note}\n"
        )
    except KeyError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: Failed to resolve task - {e}"
