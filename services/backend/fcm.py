import firebase_admin
from firebase_admin import messaging
from configs.backend.config import PROJECT_ID
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

async def send_auth_push(request_id: str, action: str, device_id: str):
    if not _firebase_initialized:
        logger.warning("Skipping FCM push — Firebase not initialized.")
        return None

    # Look up token for specific device
    from firestore import db
    doc = await db.collection("devices").document(device_id).get()
    if not doc.exists:
        logger.warning(f"No FCM token found for device {device_id}. Falling back to topic.")
        target_token = None
    else:
        target_token = doc.to_dict().get("fcm_token")

    message = messaging.Message(
        notification=messaging.Notification(
            title="Aegis Auth Request",
            body=f"Approve action on {device_id}: {action}",
        ),
        data={
            "request_id": request_id,
            "type": "auth_request"
        },
        token=target_token,
        topic="admin_approvals" if not target_token else None
    )
    from firebase_admin.exceptions import UnregisteredError
    try:
        # Wrap the blocking send in to_thread
        response = await asyncio.to_thread(messaging.send, message)
        logger.info(f"Successfully sent FCM message: {response}")
        return response
    except UnregisteredError:
        logger.warning(f"Stale FCM token for device {device_id} — removing.")
        asyncio.create_task(db.collection("devices").document(device_id).delete())
        return None
    except Exception as e:
        logger.error(f"Error sending FCM message: {e}")
        return None
