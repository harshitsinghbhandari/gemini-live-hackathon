import firebase_admin
from firebase_admin import messaging
from config import PROJECT_ID
import logging
import asyncio

logger = logging.getLogger(__name__)

_firebase_initialized = False

try:
    # Use default credentials for Cloud Run
    firebase_admin.initialize_app()
    _firebase_initialized = True
except Exception as e:
    logger.warning(
        f"Firebase Admin initialization failed: {e}. "
        "If running locally, ensure GOOGLE_APPLICATION_CREDENTIALS is set."
    )

async def send_auth_push(request_id: str, action: str, device: str):
    if not _firebase_initialized:
        logger.warning("Skipping FCM push — Firebase not initialized.")
        return None

    message = messaging.Message(
        notification=messaging.Notification(
            title="Aegis Auth Request",
            body=f"Approve action on {device}: {action}",
        ),
        data={
            "request_id": request_id,
            "type": "auth_request"
        },
        topic="admin_approvals"
    )
    try:
        # Wrap the blocking send in to_thread
        response = await asyncio.to_thread(messaging.send, message)
        logger.info(f"Successfully sent FCM message: {response}")
        return response
    except Exception as e:
        logger.error(f"Error sending FCM message: {e}")
        return None
