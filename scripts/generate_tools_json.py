import json
import os
import sys

import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())

load_dotenv()

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
COMPOSIO_USER_ID = os.environ.get("COMPOSIO_USER_ID", "harshitbhandari0318")

from composio import Composio
from aegis.tools.declarations import get_screen_tool_declarations

def generate_tools_json():
    print("🚀 Fetching tools from Composio...")
    client = Composio(api_key=COMPOSIO_API_KEY)
    tools_data = {}
    apps = ['GMAIL','GOOGLECALENDAR','GOOGLEDOCS','GOOGLESHEETS','GOOGLETASKS','GOOGLESLIDES','GITHUB']
    for app in apps:
        try:
            # Fetch all tools for the specified apps
            composio_tools = client.tools.get(
                user_id=COMPOSIO_USER_ID, 
                toolkits=[app]
            )
            print(f"✅ Found {len(composio_tools)} Composio tools for {app}")
        except Exception as e:
            print(f"❌ Failed to fetch tools: {e}")
            return

        # 1. Add Composio tools
        for tool in composio_tools:
            name = tool['function']['name']
            if not name:
                continue
            
            # We store the function declaration part that Gemini expects
            # Composio v1 tool dictionary has 'function' key
            tools_data[name] = tool['function']

    for tool in get_screen_tool_declarations():
        name = tool.get("name")
        if name:
            tools_data[name] = tool

    # Save to aegis/tools.json
    output_path = "aegis/tools.json"
    with open(output_path, "w") as f:
        json.dump(tools_data, f, indent=2)
    
    print(f"✨ Successfully generated {output_path} with {len(tools_data)} tools.")

if __name__ == "__main__":
    generate_tools_json()
