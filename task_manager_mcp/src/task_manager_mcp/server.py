from mcp.server.fastmcp import FastMCP

from .store import InMemoryTaskStore

# Shared instances
mcp = FastMCP("task_manager_mcp", host="0.0.0.0", port=8000, stateless_http=True)
store = InMemoryTaskStore()

# Import tool modules — they self-register via @mcp.tool decorator
from .tools import capture  # noqa: F401, E402
from .tools import modify  # noqa: F401, E402
from .tools import remove  # noqa: F401, E402
from .tools import resolve  # noqa: F401, E402
from .tools import review  # noqa: F401, E402
