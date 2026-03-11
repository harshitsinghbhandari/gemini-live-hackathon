import os
import json
import logging
import httpx
from . import config
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
    screen_names = [t["name"] for t in SCREEN_TOOL_DECLARATIONS]
    composio_names = list(TOOLS.keys())
    all_names = screen_names + composio_names
    return "Available tools:\n" + "\n".join(f"  {n}" for n in all_names)

def get_schemas_for(tool_names: list, context=None) -> dict:
    screen_map = {t["name"]: t for t in SCREEN_TOOL_DECLARATIONS}
    result = {}
    logger.info(f"🔍 Fetching schemas for: {tool_names}")
    for name in tool_names:
        if name in TOOLS:
            logger.info(f"   Found {name} in local tools.json")
            result[name] = TOOLS[name]
        elif name in screen_map:
            logger.info(f"   Found {name} in screen tools")
            result[name] = screen_map[name]
        elif context and context.composio:
            try:
                # Dynamic fallback to fetch schema from Composio
                logger.info(f"   Fetching {name} from Composio API...")
                url = f"https://backend.composio.dev/api/v3/tools/{name.lower()}?toolkit_versions=latest"
                headers = {"x-api-key": config.COMPOSIO_API_KEY}
                with httpx.Client() as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        schema = data.get("input_parameters") or data.get("expected_schema")
                        if schema:
                            logger.info(f"   ✅ Schema retrieved for {name}")
                            result[name] = {
                                "name": name,
                                "description": data.get("description", ""),
                                "parameters": schema
                            }
                            continue
                logger.warning(f"   ⚠️  Unknown tool: {name} (API status: {resp.status_code})")
                result[name] = {"error": f"Unknown tool: {name}"}
            except Exception as e:
                logger.error(f"   ❌ Failed to fetch schema for {name} from Composio: {e}")
                result[name] = {"error": f"Failed to fetch schema for {name}: {e}"}
        else:
            logger.warning(f"   ⚠️  Unknown tool: {name} (no context/composio)")
            result[name] = {"error": f"Unknown tool: {name}"}
    return result
