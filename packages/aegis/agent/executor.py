import logging
from typing import Dict, Any

logger = logging.getLogger("aegis.executor")

# This file is now a stub as Composio has been removed.
# Screen actions are handled by screen_executor.py.
# search_and_execute and execute_composio_tool are kept as empty stubs to avoid breaking imports elsewhere,
# though they should be removed from gate.py routing.

async def search_and_execute(action: str, tool_args: Dict[str, Any], context: Any, call_id: str = None) -> Dict[str, Any]:
    logger.warning(f"search_and_execute called with {action}, but Composio is disabled.")
    return {"success": False, "error": "External tools are disabled."}

async def execute_composio_tool(tool_name: str, tool_args: dict, context: Any, call_id: str = None) -> Dict[str, Any]:
    logger.warning(f"execute_composio_tool called with {tool_name}, but Composio is disabled.")
    return {"success": False, "error": "External tools are disabled."}
