import asyncio
import json
import logging
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from typing import List, Optional
import datetime

from models import (
    ActionLog, AuthRequest, AuthApproval, AuthStatus,
    DeviceRegistration, SessionUpdate
)
from firestore import (
    save_action_log, create_auth_request, get_auth_request,
    update_auth_status, get_audit_logs, listen_to_audit_log,
    register_device, update_session_status
)
from fcm import send_auth_push

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Aegis Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/action")
async def post_action(log: ActionLog):
    await save_action_log(log.model_dump())
    return {"status": "logged"}

@app.post("/auth/request")
async def post_auth_request(request: AuthRequest):
    request_id = await create_auth_request(request.model_dump())
    await send_auth_push(request_id, request.action, request.device)
    return {"request_id": request_id}

@app.get("/auth/pending")
async def get_pending_auth(device: str = None):
    try:
        # Fetch all pending — filter in Python to avoid composite index
        docs = db.collection("auth_requests")\
            .where("status", "==", "pending")\
            .stream()
        
        # Sort by created_at in Python
        pending = []
        for doc in docs:
            data = doc.to_dict()
            data["_id"] = doc.id
            pending.append(data)
        
        if not pending:
            return {"request_id": None}
        
        # Get oldest
        oldest = sorted(pending, key=lambda x: x.get("created_at", 0))[0]
        
        return {
            "request_id": oldest["_id"],
            "action": oldest.get("action"),
            "reason": oldest.get("reason"),
            "speak": oldest.get("speak"),
            "tool": oldest.get("tool"),
            "created_at": oldest.get("created_at").isoformat() if oldest.get("created_at") else None
        }
        
    except Exception as e:
        logger.error(f"Error fetching pending auth: {e}")
        return {"request_id": None}

@app.get("/auth/status/{request_id}", response_model=AuthStatus)
async def get_auth_status(request_id: str):
    data = await get_auth_request(request_id)
    if not data:
        raise HTTPException(status_code=404, detail="Request not found")

    # Auto-deny after 30 seconds if still pending
    created_at = data.get("created_at")
    if data["status"] == "pending" and created_at:
        now = datetime.datetime.now(datetime.timezone.utc)
        if isinstance(created_at, datetime.datetime):
            elapsed = (now - created_at).total_seconds()
            if elapsed > 30:
                await update_auth_status(request_id, False)
                return AuthStatus(status="denied")

    return AuthStatus(
        status=data["status"],
        resolved_at=data.get("resolved_at")
    )

@app.post("/auth/approve/{request_id}")
async def post_auth_approve(request_id: str, approval: AuthApproval):
    await update_auth_status(request_id, approval.approved)
    return {"status": "updated"}

@app.get("/audit/stream")
async def audit_stream(request: Request):
    loop = asyncio.get_running_loop()

    async def event_generator():
        queue = asyncio.Queue()

        def on_new_log(data):
            loop.call_soon_threadsafe(queue.put_nowait, data)

        watch = listen_to_audit_log(on_new_log)

        try:
            while True:
                if await request.is_disconnected():
                    break
                data = await queue.get()
                yield {
                    "data": json.dumps(data, default=str)
                }
        finally:
            watch.unsubscribe()

    return EventSourceResponse(event_generator())

@app.get("/audit/log")
async def audit_log(
    tier: Optional[str] = Query(None),
    limit: int = Query(50)
):
    logs = await get_audit_logs(tier=tier, limit=limit)
    return logs

@app.post("/device/register")
async def post_device_register(registration: DeviceRegistration):
    await register_device(registration.device_id, registration.fcm_token)
    return {"status": "registered"}

@app.get("/session/status")
async def get_session_status():
    from firestore import db
    doc = await db.collection("app_state").document("session").get()
    if doc.exists:
        return doc.to_dict()
    return {"is_active": False}

@app.post("/session/status")
async def post_session_status(update: SessionUpdate):
    await update_session_status(update.is_active)
    return {"status": "updated", "is_active": update.is_active}

@app.post("/session/stop")
async def post_session_stop():
    await update_session_status(False)
    return {"status": "stopped"}