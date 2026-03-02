import asyncio
from components.auth import request_touch_id

async def test():
    print("🔐 Requesting Touch ID...")
    result = await request_touch_id("Guardian Agent wants to delete tax-return-2024.pdf")
    
    if result:
        print("✅ Authenticated! Action would proceed.")
    else:
        print("❌ Denied. Action blocked.")

asyncio.run(test())