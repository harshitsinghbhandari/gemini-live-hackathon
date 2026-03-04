
import asyncio
from composio_executor import composio, USER_ID

async def main():
    # Check if already connected
    accounts = composio.connected_accounts.list(
        user_ids=[USER_ID],
        statuses=["ACTIVE"]
    )
    
    for account in accounts.items:
        print(f"Connected: {account.toolkit.slug}")
    
    # Connect Google Calendar
    connection_request = composio.toolkits.authorize(
        user_id=USER_ID,
        toolkit="googlecalendar"
    )
    print(f"\n🔗 Open this URL:\n{connection_request.redirect_url}")
    
    # Wait for connection
    connection_request.wait_for_connection(timeout=300)
    print("✅ Google Calendar connected!")

asyncio.run(main())