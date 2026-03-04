import asyncio
import json
import logging
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from typing import List, Optional
import datetime

from models import ActionLog, AuthRequest, AuthApproval, AuthStatus
from firestore import (
    save_action_log, create_auth_request, get_auth_request,
    update_auth_status, get_audit_logs, listen_to_audit_log
)
from fcm import send_auth_push

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Guardian Backend")

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