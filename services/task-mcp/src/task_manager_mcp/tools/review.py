from ..models import ReviewTaskInput
from ..server import mcp, store


@mcp.tool(
    name="review_task",
    annotations={
        "title": "Review Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def review_task(input: ReviewTaskInput) -> str:
    """Look up tasks - list, filter, search, or get details."""
    try:
        tasks = store.list(
            query=input.query,
            status=input.status,
            priority=input.priority,
            assignee=input.assignee,
            tag=input.tag,
            limit=input.limit,
        )

        if not tasks:
            return "No tasks found matching your criteria."

        lines = [f"# Tasks ({len(tasks)} found)", ""]
        for t in tasks:
            status_icon = {
                "not_started": ":white_large_square:",
                "in_progress": ":arrows_counterclockwise:",
                "done": ":white_check_mark:",
                "cancelled": ":x:",
            }.get(t.status.value, ":white_large_square:")
            priority_marker = {
                "low": ":green_circle:",
                "medium": ":yellow_circle:",
                "high": ":orange_circle:",
                "critical": ":red_circle:",
            }.get(t.priority.value, ":yellow_circle:")
            tags_str = f" [{', '.join(t.tags)}]" if t.tags else ""
            assignee_str = f" -> {t.assignee}" if t.assignee else ""
            lines.append(
                f"{status_icon} **{t.title}** "
                f"({priority_marker} {t.priority.value})"
                f"{assignee_str}{tags_str}"
            )
            lines.append(f"  - ID: `{t.id}` | Created: {t.created_at.strftime('%Y-%m-%d %H:%M')}")
            if t.resolved_at:
                lines.append(f"  - Resolved: {t.resolved_at.strftime('%Y-%m-%d %H:%M')}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: Failed to review tasks - {e}"
