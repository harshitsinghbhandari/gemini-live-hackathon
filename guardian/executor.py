import asyncio
import logging
from typing import Dict, Any
from composio import Composio
from . import config
from .context import GuardianContext

logger = logging.getLogger("guardian.executor")

async def search_and_execute(action: str, tool_args: Dict[str, Any], context: GuardianContext) -> Dict[str, Any]:
    """
    Step 1: Use Tool Router to find the right tool + plan
    Step 2: Execute it
    Returns standardized result.
    """
    if not context.composio:
        try:
            context.composio = Composio(api_key=config.COMPOSIO_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Composio: {e}")
            return {"success": False, "error": f"Composio initialization failed: {e}"}

    try:
        # Step 1: Search for the right tool
        logger.debug(f"Searching for tool: {action}")
        search_result = await asyncio.to_thread(
            context.composio.tools.execute,
            slug="COMPOSIO_SEARCH_TOOLS",
            arguments={
                "query": action,
                "limit": 1
            },
            user_id=context.user_id,
            dangerously_skip_version_check=True
        )

        if not search_result.get("successful"):
            error_msg = search_result.get("error", "Tool search failed")
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        results = search_result.get("data", {}).get("results", [])
        if not results:
            error_msg = "No tool found for this action"
            logger.warning(error_msg)
            return {"success": False, "error": error_msg}

        # Extract plan from router
        plan = results[0]
        primary_tool_slugs = plan.get("primary_tool_slugs", [])
        if not primary_tool_slugs:
            error_msg = "No primary tool slug found in plan"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        primary_tool = primary_tool_slugs[0]

        logger.info(f"🗺️  Router selected: {primary_tool}")
        recommended_steps = plan.get('recommended_plan_steps', [])
        if len(recommended_steps) > 1:
            logger.info(f"📋 Plan: {recommended_steps[1]}")

        # Step 2: Execute directly — bypass router's execution layer
        logger.debug(f"Executing tool {primary_tool} with args {tool_args}")
        execute_result = await asyncio.to_thread(
            context.composio.tools.execute,
            slug=primary_tool,
            arguments=tool_args,
            user_id=context.user_id,
            dangerously_skip_version_check=True
        )

        if execute_result.get("successful"):
            logger.info(f"✅ Successfully executed tool {primary_tool}")
            return {"success": True, "data": execute_result.get("data")}
        else:
            error_msg = execute_result.get("error", "Unknown execute error")
            logger.error(f"Tool execution failed: {error_msg}")
            return {"success": False, "error": str(error_msg)}

    except Exception as e:
        error_msg = f"Unexpected error in search_and_execute: {e}"
        logger.exception(error_msg)
        return {"success": False, "error": error_msg}
