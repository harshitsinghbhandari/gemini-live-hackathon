import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / 'packages'))
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'services' / 'backend'))

import asyncio
import json
import logging
import os
import bcrypt
from fastapi import FastAPI, HTTPException, Request, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from typing import List, Optional
import datetime

from services.backend.models import (
    ActionLog, AuthRequest, AuthApproval, AuthStatus,
    DeviceRegistration, SessionUpdate
)
from services.backend.firestore import (
    save_action_log, create_auth_request, get_auth_request,
    update_auth_status, get_audit_logs, listen_to_audit_log,
    register_device, update_session_status
)
from services.backend.fcm import send_auth_push
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
from services.backend.firestore import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Aegis Backend")

# CORS Configuration
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
else:
    allowed_origins = [
        "https://aegis.projectalpha.in",
        "https://aegisdashboard.projectalpha.in",
        "https://aegismac.projectalpha.in",
        "https://aegismobile.projectalpha.in",
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


def get_user_id(
    x_user_id: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None)
) -> str:
    """Extract user_id from X-User-ID header or query param. Defaults to harshitbhandari0318."""
    return x_user_id or user_id or "harshitbhandari0318"


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/action")
async def post_action(log: ActionLog, user_id: str = Depends(get_user_id)):
    await save_action_log(user_id, log.model_dump())
    return {"status": "logged"}

@app.post("/auth/request")
async def post_auth_request(request: AuthRequest, user_id: str = Depends(get_user_id)):
    request_id = await create_auth_request(user_id, request.model_dump())
    await send_auth_push(request_id, request.action, request.device)
    return {"request_id": request_id}

@app.get("/auth/pending")
async def get_pending_auth(device: str = None, user_id: str = Depends(get_user_id)):
    try:
        # Fetch all pending — filter in Python to avoid composite index
        docs = db.collection("users").document(user_id).collection("auth_requests")\
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
async def get_auth_status(request_id: str, user_id: str = Depends(get_user_id)):
    data = await get_auth_request(user_id, request_id)
    if not data:
        raise HTTPException(status_code=404, detail="Request not found")

    # Auto-deny after 30 seconds if still pending
    created_at = data.get("created_at")
    if data["status"] == "pending" and created_at:
        now = datetime.datetime.now(datetime.timezone.utc)
        if isinstance(created_at, datetime.datetime):
            elapsed = (now - created_at).total_seconds()
            if elapsed > 30:
                await update_auth_status(user_id, request_id, False)
                return AuthStatus(status="denied")

    return AuthStatus(
        status=data["status"],
        resolved_at=data.get("resolved_at")
    )

@app.post("/auth/approve/{request_id}")
async def post_auth_approve(request_id: str, approval: AuthApproval, user_id: str = Depends(get_user_id)):
    await update_auth_status(user_id, request_id, approval.approved)
    return {"status": "updated"}

@app.get("/audit/stream")
async def audit_stream(request: Request, user_id: str = Depends(get_user_id)):
    loop = asyncio.get_running_loop()

    async def event_generator():
        queue = asyncio.Queue()

        def on_new_log(data):
            loop.call_soon_threadsafe(queue.put_nowait, data)

        watch = listen_to_audit_log(user_id, on_new_log)

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
    limit: int = Query(50),
    user_id: str = Depends(get_user_id)
):
    logs = await get_audit_logs(user_id, tier=tier, limit=limit)
    return logs

@app.post("/device/register")
async def post_device_register(registration: DeviceRegistration, user_id: str = Depends(get_user_id)):
    await register_device(user_id, registration.device_id, registration.fcm_token)
    return {"status": "registered"}

@app.get("/session/status")
async def get_session_status(user_id: str = Depends(get_user_id)):
    from services.backend.firestore import db
    doc = await db.collection("users").document(user_id).collection("app_state").document("session").get()
    if doc.exists:
        return doc.to_dict()
    return {"is_active": False}

@app.post("/session/status")
async def post_session_status(update: SessionUpdate, user_id: str = Depends(get_user_id)):
    await update_session_status(user_id, update.is_active)
    return {"status": "updated", "is_active": update.is_active}

@app.post("/session/stop")
async def post_session_stop(user_id: str = Depends(get_user_id)):
    await update_session_status(user_id, False)
    return {"status": "stopped"}


# WebAuthn Globals
RP_ID = os.environ.get("WEBAUTHN_RP_ID", "aegismobile.projectalpha.in")
RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "Aegis")
ORIGIN = os.environ.get("WEBAUTHN_ORIGIN", "https://aegismobile.projectalpha.in")

# In-memory challenge store (production should use Redis/Firestore with TTL)
webauthn_challenges = {} 
webauthn_users = {}

@app.post("/webauthn/register/options")
async def webauthn_register_options(request: Request, user_id: str = Depends(get_user_id)):
    """Step 1 of registration — generate options for iPhone"""
    try:
        body = await request.json()
        # user_id is now retrieved from header

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
async def webauthn_register_verify(request: Request, user_id: str = Depends(get_user_id)):
    """Step 2 of registration — verify credential from iPhone"""
    body = await request.json()
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
        await db.collection("users").document(user_id).collection("webauthn_credentials").document(user_id).set({
            "credential_id": verification.credential_id.hex(),
            "public_key": verification.credential_public_key.hex(),
            "sign_count": verification.sign_count
        })

        return {"verified": True}
    except Exception as e:
        logger.error(f"WebAuthn registration error: {e}")
        return {"verified": False, "error": str(e)}

@app.post("/webauthn/auth/options")
async def webauthn_auth_options(request: Request, user_id: str = Depends(get_user_id)):
    try:
        body = await request.json()

        # Load from Firestore
        doc = await db.collection("users").document(user_id).collection("webauthn_credentials").document(user_id).get()
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
async def webauthn_auth_verify(request: Request, user_id: str = Depends(get_user_id)):
    """Verify Face ID response and approve auth request"""
    body = await request.json()
    credential = body.get("credential")
    request_id = body.get("request_id")

    doc = await db.collection("users").document(user_id).collection("webauthn_credentials").document(user_id).get()
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
        await db.collection("users").document(user_id).collection("webauthn_credentials").document(user_id).update({
            "sign_count": verification.new_sign_count
        })

        # Approve the auth request in Firestore
        if request_id:
            from services.backend.firestore import firestore as fs_lib
            await db.collection("users").document(user_id).collection("auth_requests").document(request_id).update({
                "status": "approved",
                "resolved_at": fs_lib.SERVER_TIMESTAMP
            })

        return {"verified": True}

    except Exception as e:
        logger.error(f"WebAuthn auth error: {e}")
        return {"verified": False, "error": str(e)}

@app.get("/webauthn/registered/{user_id_path}")
async def check_registered(user_id_path: str, user_id: str = Depends(get_user_id)):
    """Check if user has registered Face ID"""
    doc = await db.collection("users").document(user_id_path).collection("webauthn_credentials").document(user_id_path).get()
    return {"registered": doc.exists}

@app.post("/auth/register-pin")
async def register_pin(request: Request):
    """Register or update user PIN. No auth required for setup."""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        pin = data.get("pin")

        if not user_id or not pin:
            raise HTTPException(status_code=400, detail="Missing user_id or pin")

        # Hash the PIN
        salt = bcrypt.gensalt()
        pin_hash = bcrypt.hashpw(pin.encode('utf-8'), salt)

        # Store in Firestore: users/{user_id}/config/auth
        auth_doc = db.collection("users").document(user_id).collection("config").document("auth")
        await auth_doc.set({
            "pin_hash": pin_hash.decode('utf-8'),
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        })

        return {"success": True}
    except Exception as e:
        logger.error(f"Error registering PIN: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/verify-pin")
async def verify_pin(request: Request):
    """Verify user PIN. Returns success and user_id if valid."""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        pin = data.get("pin")

        if not user_id or not pin:
            raise HTTPException(status_code=400, detail="Missing user_id or pin")

        # Fetch pinned hash from Firestore
        auth_doc = await db.collection("users").document(user_id).collection("config").document("auth").get()
        if not auth_doc.exists:
            logger.warning(f"No PIN found for user: {user_id}")
            raise HTTPException(status_code=401, detail="Invalid ID or PIN")

        auth_data = auth_doc.to_dict()
        stored_hash = auth_data.get("pin_hash")

        if not stored_hash:
            raise HTTPException(status_code=401, detail="Invalid ID or PIN")

        # Verify PIN
        if bcrypt.checkpw(pin.encode('utf-8'), stored_hash.encode('utf-8')):
            return {"success": True, "user_id": user_id}
        else:
            raise HTTPException(status_code=401, detail="Invalid ID or PIN")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying PIN: {e}")
        raise HTTPException(status_code=500, detail=str(e))
