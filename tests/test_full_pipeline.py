import asyncio
from components.auth_gate import gate_action
import json

async def test():
    # GREEN — should execute silently
    print("=" * 50)
    result = await gate_action("send an email to john@example.com saying the project is delayed")
    filename = "data/emails.json"
    with open(filename, "w") as f:
        json.dump(result, f, indent=2)
    print("\n📋 Result:", filename)


asyncio.run(test())