# Aegis API Reference

The Aegis backend is built using FastAPI. It handles routing auth requests, maintaining session state, streaming audit logs, and WebAuthn registration/verification.

## Base URL
The backend is typically deployed at: `https://apiaegis.projectalpha.in`

## Authentication
Most endpoints require a user to be identified. This is done via two primary methods:
*   **Header:** `X-User-ID: <string>`
*   **Query Parameter:** `user_id=<string>`

If neither is provided, the backend defaults to `harshitbhandari0318`.

---

## 1. Action & Audit Endpoints

### `POST /action`
Logs an action executed (or blocked) by the local Mac agent.

*   **Headers:** `X-User-ID: <string>`
*   **Body (ActionLog):**
    ```json
    {
      "timestamp": "2023-10-27T10:00:00Z",
      "action": "Read screen",
      "tier": "GREEN",
      "tool": "screen_read",
      "arguments": {},
      "auth_used": false,
      "confirmed_verbally": false,
      "blocked": false,
      "success": true,
      "output": "The text on screen says...",
      "error": null,
      "duration_ms": 1250,
      "device": "harshit-macbook"
    }
    ```
*   **Response:** `200 OK` `{"status": "logged"}`

### `GET /audit/stream`
A Server-Sent Events (SSE) endpoint used by the Dashboard PWA to stream logs in real-time.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** `text/event-stream` stream yielding JSON strings. Includes a `comment: keepalive` every 25 seconds if active.

### `GET /audit/log`
Retrieves historical audit logs.

*   **Headers:** `X-User-ID: <string>`
*   **Query Params:** `tier` (optional, filter by GREEN/YELLOW/RED), `limit` (default 50)
*   **Response:** List of log objects.

---

## 2. Authentication Flow Endpoints (The "Gate")

### `POST /auth/request`
Called by the local agent when a RED action is intercepted. Creates a pending auth request and triggers an FCM push notification.

*   **Headers:** `X-User-ID: <string>`
*   **Body (AuthRequest):**
    ```json
    {
      "action": "Delete downloads folder",
      "tier": "RED",
      "reason": "Destructive command",
      "speak": "I need to check something before I do that.",
      "tool": "keyboard_type_sensitive",
      "arguments": {},
      "device": "harshit-macbook"
    }
    ```
*   **Response:** `200 OK` `{"request_id": "<uuid>"}`

### `GET /auth/status/{request_id}`
Called by the local agent to poll for the result of an auth request.

*   **Headers:** `X-User-ID: <string>`
*   **Behavior:** Auto-denies after 30 seconds if still pending.
*   **Response (AuthStatus):**
    ```json
    {
      "status": "pending" | "approved" | "denied",
      "resolved_at": "timestamp or null"
    }
    ```

### `GET /auth/pending`
Called by the Mobile PWA to check for the oldest pending RED action.

*   **Headers:** `X-User-ID: <string>`
*   **Query Params:** `device` (optional)
*   **Response:** Oldest pending request object or `{"request_id": null}`.

### `POST /auth/approve/{request_id}`
Manually approve or deny an auth request.

*   **Headers:** `X-User-ID: <string>`
*   **Body (AuthApproval):** `{"approved": true}`
*   **Response:** `{"status": "updated"}`

---

## 3. WebAuthn Endpoints

These endpoints manage the FIDO2/WebAuthn lifecycle for the iPhone Companion App.

### `POST /webauthn/register/options`
Step 1 of registering Face ID. Returns challenge options.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** JSON PublicKeyCredentialCreationOptions.

### `POST /webauthn/register/verify`
Step 2 of registering. Verifies the assertion and saves the public key to Firestore.

*   **Headers:** `X-User-ID: <string>`
*   **Body:** `{"credential": { ... }}`
*   **Response:** `{"verified": true}`

### `POST /webauthn/auth/options`
Step 1 of authenticating. Retrieves registered credential and generates options.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** JSON PublicKeyCredentialRequestOptions.

### `POST /webauthn/auth/verify`
Step 2 of authenticating. Verifies signature and approves the associated `request_id`.

*   **Headers:** `X-User-ID: <string>`
*   **Body:** `{"credential": { ... }, "request_id": "<uuid>"}`
*   **Response:** `{"verified": true}`

### `GET /webauthn/registered/{user_id_path}`
Checks if the user has a registered Face ID credential.

*   **Response:** `{"registered": true|false}`

---

## 4. PIN Fallback Authentication

### `POST /auth/register-pin`
Registers or updates a user PIN.

*   **Body:** `{"user_id": "string", "pin": "string"}`
*   **Response:** `{"success": true}`

### `POST /auth/verify-pin`
Verifies the PIN (rate-limited to 5/minute).

*   **Body:** `{"user_id": "string", "pin": "string"}`
*   **Response:** `{"success": true, "user_id": "string"}`

### `GET /auth/exists/{user_id}`
Checks if a user has already registered a PIN.

*   **Response:** `{"exists": true|false}`

---

## 5. Session & Device Management

### `POST /device/register`
Registers an FCM token for the mobile app.

*   **Headers:** `X-User-ID: <string>`
*   **Body (DeviceRegistration):** `{"device_id": "string", "fcm_token": "string"}`
*   **Response:** `{"status": "registered"}`

### `GET /session/status`
Checks if the local Mac agent is current active.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** `{"is_active": true|false}`

### `POST /session/status`
Updates the active status of the local agent.

*   **Headers:** `X-User-ID: <string>`
*   **Body (SessionUpdate):** `{"is_active": true}`
*   **Response:** `{"status": "updated", "is_active": true}`

### `POST /session/stop`
Forces the session to stop.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** `{"status": "stopped"}`

---

## 6. System

### `GET /health`
Returns system health and dependency status.

*   **Response:** `{"status": "ok", "timestamp": "...", "dependencies": {"gemini": "closed", "firestore": "closed", "composio": "closed"}}`