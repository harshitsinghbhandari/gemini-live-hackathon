# Verification Checklist

- [ ] P1-001: Start backend, hit an endpoint that raises an unhandled Exception, and verify a 500 JSON formatted response is returned.
- [ ] P1-002: Start the agent ws_server, trigger a CancelledError (e.g., via shutdown), and verify the "WebSocket server task cancelled" log appears and task ends cleanly.
- [ ] P2-001: Hit `/auth/pending` with valid credentials and verify it successfully fetches from Firestore using the injected `db` dependency.
- [ ] P2-002: Connect to `/audit/stream`, wait 26 seconds without activity, and verify the client receives the `{"comment": "keepalive"}` event.
- [ ] P2-003: Start backend with `LOG_FORMAT=json` and verify terminal output consists of structured JSON logs.
- [ ] P2-004: Make any request to the backend and verify the `X-Request-ID` header is present in the response.
- [ ] P2-005: Trigger OCR processing while the agent is running and verify UI/Voice streams remain responsive while `ocr_background_loop` runs in the thread pool executor.
- [ ] P2-006: Trigger a classification request (e.g. RED tier action) and verify the Gemini response does not exceed the 1024 token limit.
- [ ] P2-007: Start a multi-step agent task, set `AGENT_MAX_STEPS` to a small number (e.g., 2), and verify the loop terminates abruptly after 2 iterations.
- [ ] P3-001: Successfully authenticate a WebAuthn challenge, then replay the identical credential payload and verify it fails with "Invalid challenge".
- [ ] P3-002: Register an invalid FCM token, send a push notification, and verify the token is dynamically deleted from the `devices` collection upon `UnregisteredError`.
- [ ] P3-003: Send 6 requests to `/auth/verify-pin` within 60 seconds from the same IP and verify the 6th request returns `429 Too Many Requests`.
- [ ] P3-004: Remove local `.env` file, ensure Cloud Run instance has Secret Manager permissions, and verify the app successfully boots by pulling `FCM_KEY` directly from GCP Secret Manager.
- [ ] P3-005: Run `docker exec -it <container> whoami` on the new backend image and verify the output is `app` instead of `root`.
- [ ] P3-006: Run `pytest services/backend/test_backend.py` inside a properly provisioned virtual environment and verify all mock tests pass.
- [ ] Additional (circuit breaker): Make a request to `/health` and verify the `dependencies` mapping (gemini, firestore, composio) is surfaced correctly.
