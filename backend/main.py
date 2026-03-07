import asyncio
import json
import logging
import os
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
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType
)
from firestore import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Aegis Backend")

# CORS Configuration
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
else:
    allowed_origins = [
        "https://aegismobile.projectalpha.in",
        "https://aegismac.projectalpha.in",
        "https://aegis.projectalpha.in",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
        async for doc in docs:
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


# WebAuthn Globals
RP_ID = os.environ.get("WEBAUTHN_RP_ID", "aegismobile.projectalpha.in")
RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "Aegis")
ORIGIN = os.environ.get("WEBAUTHN_ORIGIN", "https://aegismobile.projectalpha.in")

# In-memory challenge store (production should use Redis/Firestore with TTL)
webauthn_challenges = {} 
webauthn_users = {}

@app.post("/webauthn/register/options")
async def webauthn_register_options(request: Request):
    """Step 1 of registration — generate options for iPhone"""
    try:
        body = await request.json()
        user_id = body.get("user_id", "harshit-iphone")

        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=user_id.encode('utf-8'),
            user_name=user_id,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.REQUIRED,
                resident_key=ResidentKeyRequirement.PREFERRED
            )
        )

        webauthn_challenges[user_id] = options.challenge

        return json.loads(options_to_json(options))
    except Exception as e:
        logger.error(f"WebAuthn register options error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webauthn/register/verify")
async def webauthn_register_verify(request: Request):
    """Step 2 of registration — verify credential from iPhone"""
    body = await request.json()
    user_id = body.get("user_id", "harshit-iphone")
    credential = body.get("credential")

    expected_challenge = webauthn_challenges.get(user_id)

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            require_user_verification=True
        )

        # Persist to Firestore
        await db.collection("webauthn_credentials").document(user_id).set({
            "credential_id": verification.credential_id.hex(),
            "public_key": verification.credential_public_key.hex(),
            "sign_count": verification.sign_count
        })

        return {"verified": True}
    except Exception as e:
        logger.error(f"WebAuthn registration error: {e}")
        return {"verified": False, "error": str(e)}

@app.post("/webauthn/auth/options")
async def webauthn_auth_options(request: Request):
    try:
        body = await request.json()
        user_id = body.get("user_id", "harshit-iphone")

        # Load from Firestore
        doc = await db.collection("webauthn_credentials").document(user_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="not_registered")

        data = doc.to_dict()

        # Convert hex string back to bytes
        credential_id_bytes = bytes.fromhex(data["credential_id"])

        # Cache in memory
        webauthn_users[user_id] = {
            "credential_id": credential_id_bytes,
            "public_key": bytes.fromhex(data["public_key"]),
            "sign_count": data.get("sign_count", 0)
        }

        options = generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=[
                PublicKeyCredentialDescriptor(
                    id=credential_id_bytes,
                    type=PublicKeyCredentialType.PUBLIC_KEY
                )
            ],
            user_verification=UserVerificationRequirement.REQUIRED
        )

        webauthn_challenges[user_id] = options.challenge

        return json.loads(options_to_json(options))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WebAuthn auth options error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webauthn/auth/verify")
async def webauthn_auth_verify(request: Request):
    """Verify Face ID response and approve auth request"""
    body = await request.json()
    user_id = body.get("user_id", "harshit-iphone")
    credential = body.get("credential")
    request_id = body.get("request_id")

    doc = await db.collection("webauthn_credentials").document(user_id).get()
    if not doc.exists:
        return {"verified": False, "error": "Not registered"}
    
    data = doc.to_dict()
    public_key = bytes.fromhex(data["public_key"])
    sign_count = data["sign_count"]
    expected_challenge = webauthn_challenges.get(user_id)

    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=public_key,
            credential_current_sign_count=sign_count,
            require_user_verification=True
        )

        # Update sign count
        await db.collection("webauthn_credentials").document(user_id).update({
            "sign_count": verification.new_sign_count
        })

        # Approve the auth request in Firestore
        if request_id:
            from firestore import firestore as fs_lib
            await db.collection("auth_requests").document(request_id).update({
                "status": "approved",
                "resolved_at": fs_lib.SERVER_TIMESTAMP
            })

        return {"verified": True}

    except Exception as e:
        logger.error(f"WebAuthn auth error: {e}")
        return {"verified": False, "error": str(e)}

@app.get("/webauthn/registered/{user_id}")
async def check_registered(user_id: str):
    """Check if user has registered Face ID"""
    doc = await db.collection("webauthn_credentials").document(user_id).get()
    return {"registered": doc.exists}