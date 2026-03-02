import os
import asyncio
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

composio = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
USER_ID = "harshitbhandari0318"

async def execute_action(tool_name: str, arguments: dict) -> dict:
    """
    Executes a Composio tool after auth gate clears it.
    Returns clean result or error.
    """
    try:
        response = await asyncio.to_thread(
            composio.tools.execute,
            slug=tool_name,
            arguments=arguments,
            user_id=USER_ID,
            version="latest",
            dangerously_skip_version_check=True
        )
        
        if response["successful"]:
            return {"success": True, "data": response["data"]}
        else:
            return {"success": False, "error": response["error"]}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

async def connect_app(toolkit_slug: str):
    """
    Generates OAuth URL for connecting a new app.
    Uses initiate directly to support allow_multiple.
    """
    # Get the auth config ID for the toolkit
    auth_config_id = composio.toolkits._get_auth_config_id(toolkit=toolkit_slug)
    
    # Use initiate which supports allow_multiple
    connection_request = composio.connected_accounts.initiate(
        user_id=USER_ID,
        auth_config_id=auth_config_id,
        allow_multiple=True
    )
    return connection_request.redirect_url

async def is_connected(toolkit_slug: str) -> bool:
    """
    Checks if a toolkit is connected for our user.
    """
    try:
        # Get the same auth config ID used for authorization
        auth_config_id = composio.toolkits._get_auth_config_id(toolkit=toolkit_slug)
        
        # Check specifically for active connections in that auth config
        accounts = composio.connected_accounts.list(
            user_ids=[USER_ID],
            auth_config_ids=[auth_config_id],
            statuses=["ACTIVE"]
        )
        return len(accounts.items) > 0
    except Exception as e:
        print(f"Debug: is_connected error: {e}")
        return False