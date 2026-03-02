import os
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

composio = Composio(api_key=os.environ["COMPOSIO_API_KEY"])

# Step 1: See available Gmail tools
tools = composio.tools.get("harshitbhandari0318", toolkits=["gmail"])
print("✅ Gmail tools available:")
print([tool['function']['name'] for tool in tools])
