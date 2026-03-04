import os
import asyncio
import datetime
from dotenv import load_dotenv
from composio import Composio

def log_error(error_msg: str):
    """Appends an error message with a timestamp to errors.log"""
    try:
        with open("errors.log", "a") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] ERROR: {error_msg}\n")
    except Exception:
        pass

load_dotenv()

USER_ID = "harshitbhandari0318"
composio = Composio(api_key=os.environ["COMPOSIO_API_KEY"])

async def search_and_execute(action: str, tool_args: dict) -> dict:
    """
    Step 1: Use Tool Router to find the right tool + plan
    Step 2: Execute it
    Returns clean result.
    """
    try:
        # Step 1: Search for the right tool
        search_result = await asyncio.to_thread(
            composio.tools.execute,
            slug="COMPOSIO_SEARCH_TOOLS",
            arguments={
                "query": action,
                "limit": 1
            },
            user_id=USER_ID,
            dangerously_skip_version_check=True
        )
        
        if not search_result["successful"]:
            error_msg = "Tool search failed"
            log_error(error_msg)
            return {"success": False, "error": error_msg}
        
        results = search_result["data"]["results"]
        if not results:
            error_msg = "No tool found for this action"
            log_error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Extract plan from router
        plan = results[0]
        primary_tool = plan["primary_tool_slugs"][0]
        session_id = search_result["data"]["session"]["id"]
        
        print(f"🗺️  Router selected: {primary_tool}")
        print(f"📋 Plan: {plan['recommended_plan_steps'][1]}")
        
        # Step 2: Execute directly — bypass router's execution layer
        execute_result = await asyncio.to_thread(
            composio.tools.execute,
            slug=primary_tool,
            arguments=tool_args,  # ← Gemini extracted these
            user_id=USER_ID,
            dangerously_skip_version_check=True
        )
        
        if execute_result["successful"]:
            return {"success": True, "data": execute_result["data"]}
        else:
            error_msg = execute_result.get("error", "Unknown execute error")
            log_error(str(error_msg))
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = str(e)
        log_error(error_msg)
        return {"success": False, "error": error_msg}
