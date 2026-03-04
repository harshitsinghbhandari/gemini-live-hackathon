from google.cloud import firestore
from config import PROJECT_ID
import datetime
import logging

logger = logging.getLogger(__name__)

# Async client for all async CRUD operations
db = firestore.AsyncClient(project=PROJECT_ID)

# Sync client only for on_snapshot listener (which is inherently thread-based)
db_sync = firestore.Client(project=PROJECT_ID)


async def save_action_log(data: dict):
    doc_ref = db.collection("audit_log").document()
    await doc_ref.set(data)
    return doc_ref.id


async def create_auth_request(data: dict):
    data["status"] = "pending"
    data["created_at"] = firestore.SERVER_TIMESTAMP
    data["resolved_at"] = None
    doc_ref = db.collection("auth_requests").document()
    await doc_ref.set(data)
    return doc_ref.id


async def get_auth_request(request_id: str):
    doc = await db.collection("auth_requests").document(request_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


async def update_auth_status(request_id: str, approved: bool):
    status = "approved" if approved else "denied"
    await db.collection("auth_requests").document(request_id).update({
        "status": status,
        "resolved_at": firestore.SERVER_TIMESTAMP
    })


def listen_to_audit_log(callback):
    """Uses sync client since on_snapshot is thread-based."""
    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                callback({**change.document.to_dict(), "id": change.document.id})

    col_query = (
        db_sync.collection("audit_log")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(1)
    )
    query_watch = col_query.on_snapshot(on_snapshot)
    return query_watch


async def get_audit_logs(tier: str = None, limit: int = 50):
    query = db.collection("audit_log").order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    )
    if tier:
        query = query.where(filter=firestore.FieldFilter("tier", "==", tier))

    logs = []
    async for doc in query.limit(limit).stream():
        logs.append({**doc.to_dict(), "id": doc.id})
    return logs
