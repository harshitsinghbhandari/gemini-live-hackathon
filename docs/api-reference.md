# Aegis API Reference

The Aegis backend is built using FastAPI. It handles routing auth requests, maintaining session state, streaming audit logs, and WebAuthn registration/verification.

## Base URL
The backend is typically deployed at: `https://apiaegis.projectalpha.in`

## Authentication
Most endpoints require a user to be identified. This is done via an HTTP header:
*   `X-User-ID`: The unique string identifier for the user (e.g., `harshitbhandari0318`).

---

## 1. Action & Audit Endpoints

### `POST /action`
Logs an action executed (or blocked) by the local Mac agent.

*   **Headers:** `X-User-ID: <string>`
*   **Body:**
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
*   **Response:** `200 OK` `{"status": "logged", "id": "<doc_id>"}`

### `GET /audit/stream`
A Server-Sent Events (SSE) endpoint used by the Dashboard PWA to stream logs in real-time.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** `text/event-stream` stream yielding JSON strings.

### `GET /audit/log`
Retrieves historical audit logs.

*   **Headers:** `X-User-ID: <string>`
*   **Query Params:** `tier` (optional, filter by GREEN/YELLOW/RED), `limit` (default 50)
*   **Response:** List of log objects.

---

## 2. Authentication Flow Endpoints (The "Gate")

### `POST /auth/request`
Called by the local agent when a RED action is intercepted. Creates a pending auth request.

*   **Headers:** `X-User-ID: <string>`
*   **Body:**
    ```json
    {
      "action": "Delete downloads folder",
      "tier": "RED",
      "reason": "Destructive command",
      "speak": "I need to check something before I do that.",
      "tool": "keyboard_type_sensitive",
      "arguments": {},
      "device": "harshit-macbook",
      "visual_context": {
         "base64_image": "iVBORw0KG...",
         "mime_type": "image/jpeg",
         "action_description": "Delete downloads folder",
         "element_label": "keyboard_type_sensitive"
      }
    }
    ```
*   **Response:** `200 OK` `{"status": "requested", "request_id": "<uuid>"}`

### `GET /auth/status/{request_id}`
Called by the local agent to poll for the result of an auth request.

*   **Headers:** `X-User-ID: <string>`
*   **Response:**
    ```json
    {
      "request_id": "<uuid>",
      "status": "pending" | "approved" | "denied" | "expired",
      "resolved_at": "timestamp or null"
    }
    ```

### `GET /auth/pending`
Called by the Mobile PWA to check if there are any pending RED actions requiring biometric approval.

*   **Headers:** `X-User-ID: <string>`
*   **Query Params:** `device` (optional)
*   **Response:** List of pending request objects including `visual_context`.

### `POST /auth/approve/{request_id}`
(Legacy/Fallback) Endpoint to manually approve/deny a request without WebAuthn.

*   **Headers:** `X-User-ID: <string>`
*   **Body:** `{"approved": true}`
*   **Response:** `200 OK`

---

## 3. WebAuthn Endpoints

These endpoints manage the FIDO2/WebAuthn lifecycle for the iPhone Companion App.

### `POST /webauthn/register/options`
Step 1 of registering Face ID. Returns challenge options.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** JSON PublicKeyCredentialCreationOptions.

### `POST /webauthn/register/verify`
Step 2 of registering. Verifies the assertion from the device and saves the public key to Firestore.

*   **Headers:** `X-User-ID: <string>`
*   **Body:** `{"credential": { ... }}`
*   **Response:** `{"verified": true}`

### `POST /webauthn/auth/options`
Step 1 of authenticating a specific pending request.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** JSON PublicKeyCredentialRequestOptions.

### `POST /webauthn/auth/verify`
Step 2 of authenticating. Verifies the signed payload using the stored public key and approves the associated `request_id`.

*   **Headers:** `X-User-ID: <string>`
*   **Body:** `{"credential": { ... }, "request_id": "<uuid>"}`
*   **Response:** `{"verified": true}`

### `GET /webauthn/registered/{user_id_path}`
Checks if the user has a registered Face ID credential.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** `{"registered": true|false}`

---

## 4. PIN Fallback Authentication

### `POST /auth/register-pin`
Registers a fallback PIN for the user. (No `X-User-ID` header required, payload contains ID).

*   **Body:** `{"user_id": "harshitbhandari0318", "pin": "1234"}`
*   **Response:** `{"success": true}`

### `POST /auth/verify-pin`
Verifies the PIN (rate-limited to 5/minute).

*   **Body:** `{"user_id": "harshitbhandari0318", "pin": "1234"}`
*   **Response:** `{"success": true, "user_id": "harshitbhandari0318"}`

---

## 5. Session & Device Management

### `POST /device/register`
Registers an FCM (Firebase Cloud Messaging) token for the mobile app (used for push notifications if configured).

*   **Headers:** `X-User-ID: <string>`
*   **Body:** `{"device_id": "iphone", "fcm_token": "..."}`
*   **Response:** `{"status": "registered"}`

### `GET /session/status`
Checks if the local Mac agent is currently active.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** `{"is_active": true|false}`

### `POST /session/status`
Updates the active status of the local agent.

*   **Headers:** `X-User-ID: <string>`
*   **Body:** `{"is_active": true}`
*   **Response:** `{"status": "updated", "is_active": true}`

### `POST /session/stop`
Forces the session to stop.

*   **Headers:** `X-User-ID: <string>`
*   **Response:** `{"status": "stopped"}`

---

## 6. System

### `GET /health`
Returns system health, including the status of dependencies like Firestore.

*   **Response:** `{"status": "ok", "timestamp": "...", "dependencies": {"firestore": "ok"}}`