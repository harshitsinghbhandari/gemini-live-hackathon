import asyncio
import sys
import os

# Add root project directory to sys.path so 'components' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from components.auth_gate import gate_action
import json

async def test():
    # GREEN — should execute silently
    print("=" * 50)
    result = result = await gate_action("what are my calendar events today")
    filename = "data/emails.json"
    with open(filename, "w") as f:
        json.dump(result, f, indent=2)
    print("\n📋 Result:", filename)


asyncio.run(test())