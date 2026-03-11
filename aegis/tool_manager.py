import os
import json
import logging
from .screen_executor import SCREEN_TOOL_DECLARATIONS

logger = logging.getLogger("aegis.tool_manager")

def load_tools():
    path = os.path.join(os.path.dirname(__file__), "tools.json")
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load tools.json: {e}")
    return {}

TOOLS = load_tools()

def get_tool_names_prompt():
    # Only return tools present in tools.json (which we've truncated to screen tools)
    # and the explicit SCREEN_TOOL_DECLARATIONS.
    all_names = list(TOOLS.keys())
    return "Available tools:\n" + "\n".join(f"  {n}" for n in all_names)

def get_schemas_for(tool_names: list, context=None) -> dict:
    result = {}
    logger.info(f"🔍 Fetching schemas for: {tool_names}")
    for name in tool_names:
        if name in TOOLS:
            logger.info(f"   Found {name} in local tools.json")
            result[name] = TOOLS[name]
        else:
            logger.warning(f"   ⚠️  Unknown tool: {name}")
            result[name] = {"error": f"Unknown tool: {name}"}
    return result
