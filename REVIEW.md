# Aegis — Deep Systems Audit

Date: 2025-05-15
Files reviewed: 42
Total issues found: 12

---

# System Map

## Environment Variables
- `GOOGLE_API_KEY`: Gemini API key (Python)
- `COMPOSIO_API_KEY`: Composio API key (Python)
- `USER_ID`: Unique user identifier (Python)
- `BACKEND_URL`: URL for the FastAPI backend (Python)
- `DASHBOARD_URL`: URL for the React dashboard (Python)
- `VITE_BACKEND_URL`: URL for the backend used by the Vite dashboard (JS)
- `PROJECT_ID`: GCP Project ID (Python)
- `FCM_KEY`: Firebase Cloud Messaging key (Python/Backend)

## Backend Endpoints
- `GET /health`: Health check
- `POST /action`: Log an action (Called by `aegis/gate.py`)
- `POST /auth/request`: Request remote authentication (Called by `aegis/gate.py`)
- `GET /auth/pending`: Poll for pending requests (Called by `mobile-app/src/hooks/usePendingAuth.js`)
- `GET /auth/status/{request_id}`: Check auth status (Called by `aegis/gate.py`, `mac-app/src/pages/RedAuthPage.jsx`)
- `POST /auth/approve/{request_id}`: Approve/Deny request (Called by `mobile-app/src/pages/RedAuthPage.jsx`)
- `GET /audit/stream`: SSE stream for audit logs (Called by `dashboard/src/hooks/useAuditStream.js`, `mobile-app/src/hooks/useAuditMirror.js`)
- `GET /audit/log`: Fetch history (Called by `dashboard/src/hooks/useAuditLog.js`, `mobile-app/src/hooks/useAuditMirror.js`)
- `POST /device/register`: Register FCM token (Called by `mobile-app/src/components/FaceIDButton.jsx`)
- `GET /session/status`: Check if session is active (Called by `aegis/voice.py`)
- `POST /session/status`: Update session activity (Called by `aegis/voice.py`)
- `POST /session/stop`: Remote kill switch (Called by `mobile-app/src/pages/MirrorPage.jsx`)
- `POST /webauthn/*`: Multiple endpoints for FaceID registration and verification.

## WebSocket Events
**Emitted by `aegis/ws_server.py`:**
- `status`: Agent status (idle, listening, executing, etc.)
- `waveform`: Mic amplitude for UI visualization
- `session_started`: New session initialization
- `session_ended`: Session cleanup
- `red_auth_started`: Trigger RED auth overlay in Mac App
- `red_auth_result`: Broadcast result of RED auth
- `yellow_confirm`: Trigger YELLOW confirmation overlay
- `action`: Broadcast completed action card

**Listened by `aegis/ws_server.py`:**
- `yellow_response`: (Unused) Intended for UI-based confirmation.

## JSON Schemas
- **Action Log**: `timestamp`, `action`, `tier`, `tool`, `arguments`, `auth_used`, `confirmed_verbally`, `blocked`, `success`, `error`, `duration_ms`, `device`.
- **Auth Request**: `action`, `tier`, `reason`, `speak`, `tool`, `arguments`, `device`.
- **WebSocket Action**: Similar to Action Log but includes `toolkit` and `upgraded`.

## Risk Tier System
- **Tiers**: `GREEN`, `YELLOW`, `RED`.
- **Consistency**:
    - `classifier.py`: Correctly uses upper-case strings.
    - `gate.py`: Correctly uses upper-case strings.
    - `dashboard/`: Correctly uses upper-case strings for styling and labels.
    - `mobile-app/`: Mostly upper-case in labels, but some CSS classes and internal logic use lower-case (e.g., `ActionCard.jsx` uses `tier.toLowerCase()`).
- **Detection**: No functional mismatch found, but naming conventions vary between logic (snake_case/UPPER) and UI (camelCase/lower).

## Ports and URLs
- **Agent WebSocket**: `localhost:8765`
- **Helper Server**: `localhost:8766`
- **Backend (Dev)**: `localhost:8080`
- **Dashboard (Dev)**: `localhost:3000`
- **Production URL**: `https://apiaegis.projectalpha.in` (Backend), `https://aegis.projectalpha.in` (Dashboard), `https://aegismac.projectalpha.in` (Mac App).

---

# Category 1 — CRITICAL (1)

CRITICAL-001
File: `aegis/gate.py`
Line: 122-132

Issue: **Request ID Mismatch**. The `red_auth_started` event is broadcast with a locally generated UUID as `request_id` *before* the backend request is made. The Mac App uses this ID to poll `/auth/status/{request_id}`. However, the backend generates its own `request_id` upon receiving the POST request.

Impact: The Mac App polls the wrong endpoint (a non-existent local UUID) and will never receive the update from the backend, resulting in a permanent hang on the "Requires your approval" screen until timeout.

Fix: Move the `ws_server.broadcast` call after `request_remote_auth` is initiated, or update the Mac App to listen for a second event that provides the real `request_id`.

---

# Category 2 — INTEGRATION (5)

ISSUE-001
File: `aegis/gate.py`
Line: 189-192

Issue: **Audit Log Data Loss**. Tool output is truncated to 1000 characters before being posted to the backend and broadcast to the UI.

Impact: Large tool outputs (e.g., list of 50 emails) are permanently lost from the audit history in Firestore.

Fix: Only truncate for the WebSocket broadcast, not for the backend POST or local audit logger.

ISSUE-002
File: `mobile-app/src/hooks/usePendingAuth.js`
Line: 21-25

Issue: **Misleading Code Comments**. The hook contains comments stating that `/auth/pending` does not exist in `main.py` and that it's being implemented "as requested" blindly.

Impact: Confusion for future developers; it suggests a mismatch that doesn't actually exist (the endpoint IS in `main.py`).

Fix: Remove the misleading comments.

ISSUE-003
File: `backend/fcm.py`
Line: 35-43

Issue: **Generic FCM Topic**. Auth requests are sent to a global topic `admin_approvals` instead of a device-specific token, despite `device_id` being available.

Impact: Every registered mobile device receives every auth request for every Mac agent.

Fix: Use the `device_id` to look up the specific FCM token in Firestore and send a targeted message.

ISSUE-004
File: `mobile-app/src/pages/RedAuthPage.jsx`
Line: 6

Issue: **Missing `speak` field**. The mobile app Red Auth screen extracts `action`, `reason`, and `created_at` but ignores the `speak` field provided by the backend.

Impact: The mobile user doesn't see the specific audible instruction generated by Gemini.

Fix: Add the `speak` field to the UI display.

ISSUE-005
File: `dashboard/src/hooks/useAuditLog.js`
Line: 4

Issue: **Hardcoded Backend Proxy Expectation**. The dashboard expects a `/audit` proxy or `VITE_BACKEND_URL` but fallback logic is inconsistent with other apps.

Impact: Local development is brittle if the Vite proxy isn't configured exactly.

Fix: Standardize backend URL resolution across all frontend apps.

---

# Category 3 — FRAGILITY (6)

QUALITY-001
File: `aegis_menubar.py`
Line: 50

Issue: **Hardcoded Session Timeout**. There is a 60-second `threading.Timer` that kills the session automatically.

Impact: Users are cut off mid-conversation if the session lasts more than a minute.

Fix: Remove the timer or make it configurable/longer.

QUALITY-002
File: `aegis/voice.py`
Line: 195

Issue: **Inefficient Polling**. The agent polls `GET /session/status` every 5 seconds to support the remote kill switch.

Impact: Unnecessary backend load and battery drain.

Fix: Use a long-lived WebSocket or SSE connection for session control.

QUALITY-003
File: `aegis/executor.py`
Line: 16

Issue: **Implicit Composio Initialization**. Composio is initialized inside the execution loop rather than at startup.

Impact: First tool execution is delayed by authentication/init overhead.

Fix: Initialize Composio in the `AegisContext` at startup.

QUALITY-004
File: `mac-app/src/config.js` and `mobile-app/src/config.js`

Issue: **Hardcoded Production URLs**. Production URLs are hardcoded in source files instead of being injected via environment variables.

Impact: Difficulty in deploying to different environments (staging/beta).

Fix: Use Vite environment variables (`import.meta.env`).

QUALITY-005
File: `aegis/ws_server.py`
Line: 29

Issue: **Dead Event Listener**. The server listens for `yellow_response` but no client sends it.

Impact: Dead code.

Fix: Remove or implement the corresponding UI functionality.

QUALITY-006
File: `aegis/screen.py`
Line: 11

Issue: **Unused Feature**. Screen capture is implemented but never called by the voice agent.

Impact: Dead code / Bloat.

Fix: Integrate screen context into the Gemini prompt or remove if not needed.

---

# Priority Fix Order

1. **CRITICAL-001**: Fix the Request ID mismatch to enable remote auth.
2. **ISSUE-003**: Fix FCM targeting to prevent notification spam.
3. **ISSUE-001**: Stop truncating audit log data.
4. **QUALITY-001**: Remove/increase the 60s session limit.

---

# Estimated Fix Time

CRITICAL | 1 issue | 1.5 hours
INTEGRATION | 5 issues | 4 hours
QUALITY | 6 issues | 4 hours

Total | 9.5 hours
