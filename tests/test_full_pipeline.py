import asyncio
import sys
import os
import json
import logging

# Add root project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from aegis.gate import gate_action
from aegis.context import AegisContext
from aegis.config import setup_logging, USER_ID

async def test():
    # Setup logging to see results
    setup_logging()

    # Initialize context
    context = AegisContext(user_id=USER_ID)

    # GREEN — should execute silently (reading calendar)
    print("=" * 50)
    print("Test: Reading calendar (GREEN)")
    result = await gate_action("what are my calendar events today", context)

    filename = "data/calendar_test_result.json"
    os.makedirs("data", exist_ok=True)
    with open(filename, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n📋 Result saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(test())
