import asyncio
import sys
import os

# Add root project directory to sys.path so 'components' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from components.auth_gate import gate_action

async def fake_execute():
    return "Action executed successfully"

async def test():
    # Test RED — should trigger Touch ID
    result = await gate_action(
        "delete folder tax-return-2024 from Desktop",
        fake_execute
    )
    print("\n📋 Result:", result)

asyncio.run(test())