import asyncio
import sys
import os

# Add root project directory to sys.path so 'components' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from components.composio_executor import composio, USER_ID

def test():
    # Search for gmail tools via router
    result = composio.tools.execute(
        slug="COMPOSIO_SEARCH_TOOLS",
        arguments={
            "query": "fetch my latest emails",
            "limit": 3
        },
        user_id=USER_ID,
        dangerously_skip_version_check=True
    )
    print("Search result:", result)

test()