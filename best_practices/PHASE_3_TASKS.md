# Phase 3 Tasks: Infrastructure & Long-Term

- **Task ID**: P3-001
- **Title**: Expire WebAuthn Challenges Server-Side
- **File(s)**: `cmd/backend/run_backend.py`
- **Current code**:
```python
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
```
- **Proposed change**:
```python
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

        # Clear challenge immediately to prevent replay attacks
        webauthn_challenges.pop(user_id, None)

        # Update sign count
```
- **Test**: Attempt a replay attack with an already-used credential response. The second attempt should fail with `Invalid challenge`.
- **Rollback**: Remove `webauthn_challenges.pop(user_id, None)`.
- **Breaks anything?**: No. Enhances security by enforcing one-time use.
- **What to validate before**: Ensure existing WebAuthn endpoints work.
- **What to validate after**: Confirm a user can successfully authenticate and that subsequent identical requests are blocked.

---

- **Task ID**: P3-002
- **Title**: Handle FCM Token Expiry
- **File(s)**: `services/backend/fcm.py`
- **Current code**:
```python
    try:
        # Wrap the blocking send in to_thread
        response = await asyncio.to_thread(messaging.send, message)
        logger.info(f"Successfully sent FCM message: {response}")
        return response
    except Exception as e:
        logger.error(f"Error sending FCM message: {e}")
        return None
```
- **Proposed change**:
```python
    from firebase_admin.exceptions import UnregisteredError

    try:
        # Wrap the blocking send in to_thread
        response = await asyncio.to_thread(messaging.send, message)
        logger.info(f"Successfully sent FCM message: {response}")
        return response
    except UnregisteredError:
        logger.warning(f"Stale FCM token for device {device_id} — removing.")
        from services.backend.firestore import db
        asyncio.create_task(db.collection("devices").document(device_id).delete())
        return None
    except Exception as e:
        logger.error(f"Error sending FCM message: {e}")
        return None
```
- **Test**: Send a test push notification to an unregistered device token and verify the `UnregisteredError` logic triggers successfully.
- **Rollback**: Remove the explicit `UnregisteredError` except block.
- **Breaks anything?**: No. Cleans up stale data proactively.
- **What to validate before**: Check if stale tokens accumulate.
- **What to validate after**: Confirm invalid tokens are dynamically dropped from the `devices` collection.

---

- **Task ID**: P3-003
- **Title**: Add rate-limiting with slowapi
- **File(s)**: `cmd/backend/run_backend.py`
- **New dependency**: `slowapi==0.1.9`
- **Conflicts check**: None known in `requirements.txt`.
- **Current code**:
```python
@app.post("/auth/verify-pin")
async def verify_pin(request: Request):
```
- **Proposed change**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/auth/verify-pin")
@limiter.limit("5/minute")
async def verify_pin(request: Request):
```
- **Test**: Attempt to call `/auth/verify-pin` 6 times within 60 seconds. The 6th request must yield a `429 Too Many Requests`.
- **Rollback**: Remove the `@limiter` decorator and initialization.
- **Breaks anything?**: No. Protects the PIN fallback.
- **What to validate before**: Execute multiple bad PIN requests quickly and observe all return 401s.
- **What to validate after**: Ensure 429s replace 401s when the threshold is crossed.

---

- **Task ID**: P3-004
- **Title**: Move Secrets to Google Cloud Secret Manager
- **File(s)**: `configs/backend/config.py`, `cmd/backend/run_backend.py`
- **Current code**: (Using `.env` files and `os.environ.get`)
- **Proposed change**:
  1. Enable the Secret Manager API: `gcloud services enable secretmanager.googleapis.com`
  2. Create secrets for environment variables:
     ```bash
     gcloud secrets create aegis-backend-url --replication-policy="automatic"
     echo -n "https://apiaegis.projectalpha.in" | gcloud secrets versions add aegis-backend-url --data-file=-
     ```
  3. Grant the Cloud Run service account `roles/secretmanager.secretAccessor`.
  4. Update backend config loader to query Secret Manager directly or use Cloud Run native secret mapping.
- **Test**: See below
- **Rollback**: Revert to `os.environ.get` logic
- **Breaks anything?**: Requires infrastructure state modifications.
- **What to validate before**: Ensure the app fails to start locally if `.env` is missing.
- **What to validate after**: Start the container locally mapping `GOOGLE_APPLICATION_CREDENTIALS` and ensure configuration loads successfully from GCP without a `.env` file.

---

- **Task ID**: P3-005
- **Title**: Harden Dockerfile (Non-Root, Multi-Stage, Pinned Base)
- **File(s)**: `services/backend/Dockerfile`
- **Current code**: `FROM python:3.11-slim` running as root user.
- **Proposed change**:
  1. Replace `FROM python:3.11-slim` with a specific digest `FROM python:3.11.9-slim-bookworm AS builder`.
  2. Add a builder stage:
     ```dockerfile
     FROM python:3.11.9-slim-bookworm AS builder
     COPY services/backend/requirements.txt .
     RUN pip install --user --no-cache-dir -r requirements.txt
     ```
  3. Create the final runtime image with a non-root user:
     ```dockerfile
     FROM python:3.11.9-slim-bookworm
     RUN addgroup --system app && adduser --system --ingroup app app
     USER app
     COPY --from=builder /root/.local /home/app/.local
     ENV PATH=/home/app/.local/bin:$PATH
     COPY --chown=app:app . /app
     WORKDIR /app
     CMD ["uvicorn", "cmd.backend.run_backend:app", "--host", "0.0.0.0", "--port", "8080"]
     ```
- **Test**: Build container image and verify start.
- **Rollback**: `git revert` the Dockerfile modifications.
- **Breaks anything?**: Permission paths for files writing to local disk might need updates.
- **What to validate before**: Run `docker exec -it <container> whoami` on the old image and assert the output is `root`.
- **What to validate after**: Run `docker exec -it <container> whoami` and assert the output is `app`.

---

- **Task ID**: P3-006
- **Title**: Replace ad-hoc test scripts with Pytest suites
- **File(s)**: `services/backend/test_backend.py`, root test scripts
- **Current code**: Ad-hoc Python script execution testing.
- **Proposed change**:
  1. Remove `testOCR.py`, `testOllamaOCR.py`.
  2. Initialize `services/backend/tests/test_run_backend.py`.
  3. Use `pytest-asyncio` and mock `google.cloud.firestore.AsyncClient` + `firebase_admin`.
  4. Setup a GitHub Action invoking `pytest --cov=. --cov-fail-under=70`.
- **Test**: Execute `pytest` command natively.
- **Rollback**: Revert `.github` workflow modifications.
- **Breaks anything?**: Replaces broken testing infrastructure.
- **What to validate before**: Attempt to run `pytest` and observe minimal coverage.
- **What to validate after**: Run the CI pipeline locally and verify test mocks correctly intercept external API calls without network access.
