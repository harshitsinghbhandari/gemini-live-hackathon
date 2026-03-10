import os
import json
import logging
import httpx
from . import config
from .screen_executor import SCREEN_TOOL_DECLARATIONS

logger = logging.getLogger("aegis.tool_manager")

def load_tools():
    """Loads pre-cached tools from tools.json."""
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
    """
    Returns a list of all available tool names (Screen + Composio) to inform the model's lazy loading decisions.
    """
    screen_names = [t["name"] for t in SCREEN_TOOL_DECLARATIONS]
    composio_names = list(TOOLS.keys())
    all_names = sorted(list(set(screen_names + composio_names)))
    return "Available tool names (call get_tool_schema for details):\n" + "\n".join(f"  {n}" for n in all_names)

def get_schemas_for(tool_names: list, context=None) -> dict:
    """
    Lazy-loads tool schemas. Checks local cache first, then dynamic screen tools,
    and finally falls back to the Composio API.
    """
    screen_map = {t["name"]: t for t in SCREEN_TOOL_DECLARATIONS}
    result = {}
    logger.info(f"🔍 Lazy-fetching schemas for: {tool_names}")

    for name in tool_names:
        # 1. Local Cache (tools.json)
        if name in TOOLS:
            logger.debug(f"   Found {name} in local tools.json")
            result[name] = TOOLS[name]

        # 2. Screen Tools (Specialized local drivers)
        elif name in screen_map:
            logger.debug(f"   Found {name} in screen tools")
            result[name] = screen_map[name]

        # 3. Dynamic Fallback (Composio API)
        elif context and context.composio:
            try:
                logger.info(f"   Fetching {name} from Composio API (Lazy Load)...")
                # We normalize the name for the API call
                api_name = name.lower()
                url = f"https://backend.composio.dev/api/v3/tools/{api_name}?toolkit_versions=latest"
                headers = {"x-api-key": config.COMPOSIO_API_KEY}

                with httpx.Client() as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        schema = data.get("input_parameters") or data.get("expected_schema")
                        if schema:
                            logger.info(f"   ✅ Schema retrieved for {name}")
                            # Inject into TOOLS cache for this session to avoid re-fetching
                            TOOLS[name] = {
                                "name": name,
                                "description": data.get("description", ""),
                                "parameters": schema
                            }
                            result[name] = TOOLS[name]
                            continue

                logger.warning(f"   ⚠️  Unknown tool requested: {name} (API status: {resp.status_code})")
                result[name] = {"error": f"Unknown tool: {name}"}
            except Exception as e:
                logger.error(f"   ❌ Failed to lazy-fetch {name} from Composio: {e}")
                result[name] = {"error": f"Failed to fetch schema for {name}: {e}"}

        else:
            logger.warning(f"   ⚠️  Cannot fetch schema for {name}: No Composio context available.")
            result[name] = {"error": f"Unknown tool: {name}"}

    return result
