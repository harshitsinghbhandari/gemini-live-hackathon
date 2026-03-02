import asyncio
from .composio_executor import connect_app, is_connected

async def main():
    # Check if already connected
    if await is_connected("gmail"):
        print("✅ Gmail already connected!")
        return
        
    # Generate OAuth URL
    url = await connect_app("gmail")
    print(f"\n🔗 Open this URL in your browser to connect Gmail:\n{url}")
    print("\nCome back after authorizing.")

asyncio.run(main())