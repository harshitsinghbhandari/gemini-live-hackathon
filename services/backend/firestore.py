from google.cloud import firestore
import os
import datetime
import logging

logger = logging.getLogger(__name__)

# Async client for all async CRUD operations
db = firestore.AsyncClient(project=os.environ.get("PROJECT_ID"))

# Sync client only for on_snapshot listener (which is inherently thread-based)
db_sync = firestore.Client(project=os.environ.get("PROJECT_ID"))

def get_user_collection_sync(user_id: str, collection: str):
    return db_sync.collection("users").document(user_id).collection(collection)

def get_user_collection(user_id: str, collection: str):
    return db.collection("users").document(user_id).collection(collection)


async def save_action_log(user_id: str, data: dict):
    doc_ref = get_user_collection(user_id, "audit_log").document()
    await doc_ref.set(data)
    return doc_ref.id


async def create_auth_request(user_id: str, data: dict):
    data["status"] = "pending"
    data["created_at"] = firestore.SERVER_TIMESTAMP
    data["resolved_at"] = None
    doc_ref = get_user_collection(user_id, "auth_requests").document()
    await doc_ref.set(data)
    return doc_ref.id


async def get_auth_request(user_id: str, request_id: str):
    doc = await get_user_collection(user_id, "auth_requests").document(request_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


async def update_auth_status(user_id: str, request_id: str, approved: bool):
    status = "approved" if approved else "denied"
    await get_user_collection(user_id, "auth_requests").document(request_id).update({
        "status": status,
        "resolved_at": firestore.SERVER_TIMESTAMP
    })


def listen_to_audit_log(user_id: str, callback):
    """Uses sync client since on_snapshot is thread-based."""
    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                callback({**change.document.to_dict(), "id": change.document.id})

    col_query = (
        get_user_collection_sync(user_id, "audit_log")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(1)
    )
    query_watch = col_query.on_snapshot(on_snapshot)
    return query_watch


async def get_audit_logs(user_id: str, tier: str = None, limit: int = 50):
    query = get_user_collection(user_id, "audit_log").order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    )
    if tier:
        query = query.where(filter=firestore.FieldFilter("tier", "==", tier))

    logs = []
    async for doc in query.limit(limit).stream():
        logs.append({**doc.to_dict(), "id": doc.id})
    return logs


async def register_device(user_id: str, device_id: str, fcm_token: str):
    await get_user_collection(user_id, "devices").document(device_id).set({
        "fcm_token": fcm_token,
        "updated_at": firestore.SERVER_TIMESTAMP
    })


async def update_session_status(user_id: str, is_active: bool):
    await get_user_collection(user_id, "app_state").document("session").set({
        "is_active": is_active,
        "updated_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
