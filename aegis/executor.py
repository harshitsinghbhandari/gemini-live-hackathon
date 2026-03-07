import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Dict, Any
from composio import Composio
from google import genai
from . import config
from .context import AegisContext

logger = logging.getLogger("aegis.executor")

SUPPORTED_TOOLKITS = [
    "gmail",
    "googlecalendar",
    "googledocs",
    "googlesheets",
    "googleslides",
    "googletasks",
    "github"
]

async def fill_arguments(
    tool_slug: str,
    partial_args: dict,
    user_command: str,
    context: AegisContext
) -> dict:
    """
    Fetch tool schema from Composio, send to Gemini,
    get back complete arguments.
    """
    if not context.composio:
        return partial_args

    # Step 1: Fetch schema for this specific tool
    # Step 1: Fetch schema for this specific tool
    try:
        tools = await asyncio.to_thread(
            context.composio.tools.get,
            user_id=context.user_id,
            toolkits=SUPPORTED_TOOLKITS
        )
    except Exception as e:
        logger.error(f"Failed to fetch tools for schema: {e}")
    # Step 1: Fetch schema for this specific tool by querying its endpoint
    import httpx
    tool_schema = None
    try:
        url = f"https://backend.composio.dev/api/v3/tools/{tool_slug}?toolkit_versions=latest"
        headers = {"x-api-key": config.COMPOSIO_API_KEY}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # Composio V3 tool schema structure
                tool_schema = data.get("input_parameters") or data.get("expected_schema")
    except Exception as e:
        logger.warning(f"Failed to fetch schema for {tool_slug} via API: {e}")
            
    if not tool_schema:
        print(f"DEBUG {tool_slug}: No schema found. Returning partial args.")
        # Schema not found, return partial args as-is
        return partial_args
    
    # Step 2: Ask Gemini to fill complete arguments
    # Convert tool_schema to dict if it's a model
    if hasattr(tool_schema, "model_dump"):
        schema_dict = tool_schema.model_dump()
    elif hasattr(tool_schema, "__dict__"):
        schema_dict = tool_schema.__dict__
    else:
        schema_dict = tool_schema

    schema_str = json.dumps(schema_dict, indent=2)

    prompt = f"""
You are filling in arguments for a tool call.

User said: "{user_command}"

Tool: {tool_slug}
Schema: {schema_str}

Partial arguments already extracted: {json.dumps(partial_args, indent=2)}

Today's date: {datetime.now().isoformat()}

Rules:
- Fill ALL required fields
- Use partial_args as-is if already correct
- For missing required fields, infer from user command
- For IDs you don't know (like tasklist_id), use "@default"
- For GitHub requests, use the user's primary repo if known or guess "harshitbhandari0318" for owner and "gemini-live-hackathon" for repo
- For dates, use RFC3339 format
- Return ONLY valid JSON with complete arguments, nothing else
- Do not include read-only fields

Return complete arguments JSON:
"""
    print(f"Gemini schema prompt:\n{prompt}")
    logger.debug(f"Gemini schema prompt:\n{prompt}")
    try:
        gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
        response = await gemini_client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt
        )
        
        raw = response.text.strip()
        # Strip markdown if present
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        
        complete_args = json.loads(raw)
        return complete_args
    except json.JSONDecodeError:
        logger.warning(f"Could not parse Gemini args response, using partial: {raw}")
        return partial_args
    except Exception as e:
        logger.error(f"Error in Gemini argument filling: {e}")
        return partial_args

async def search_and_execute(action: str, tool_args: Dict[str, Any], context: AegisContext) -> Dict[str, Any]:
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
                "limit": 1,
                "toolkits": SUPPORTED_TOOLKITS
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

        # Step 2: Fill arguments
        complete_args = await fill_arguments(
            tool_slug=primary_tool,
            partial_args=tool_args,
            user_command=action,
            context=context
        )

        # Step 3: Execute directly — bypass router's execution layer
        logger.info(f"Executing {primary_tool} with complete args: {json.dumps(complete_args, indent=2)}")
        execute_result = await asyncio.to_thread(
            context.composio.tools.execute,
            slug=primary_tool,
            arguments=complete_args,
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
