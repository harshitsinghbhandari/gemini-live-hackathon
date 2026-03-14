# Master Implementation Plan

This plan organizes the production readiness audit findings into three logical phases. Each phase is prioritized by risk reduction and blast radius, ensuring the codebase remains working after each step.

---

## Phase 1 — Critical & Safe (No behavior change, no new dependencies)
**Phase Goal:** Fix immediate security and reliability risks without altering external APIs, modifying schemas, or changing the AI agent loop logic. These changes are isolated and can be shipped independently.

**Phase 1 Tasks:**
1. **Add global exception handler to FastAPI**
   - **File:** `cmd/backend/run_backend.py`
   - **Effort:** S
   - **Why:** The API currently leaks raw stack traces to the client on unhandled exceptions (e.g., inside the `/action` or `/auth` endpoints). We need to return structured JSON errors.
2. **Enforce explicit CancelledError propagation**
   - **File:** `packages/aegis/interfaces/ws_server.py`
   - **Effort:** S
   - **Why:** The WebSocket server catches `asyncio.CancelledError` but fails to re-raise it, causing silent failures and preventing the event loop from shutting down cleanly.

---

## Phase 2 — Structural Improvements (Moderate risk, well-contained)
**Phase Goal:** Improve internal architecture and add missing foundational patterns (like dependency injection and JSON logging). Introduces some explicit dependencies but no external contract changes.

**Phase 2 Tasks:**
1. **Add Dependency Injection for Firestore instances**
   - **File:** `cmd/backend/run_backend.py`
   - **Effort:** M
   - **Why:** The backend uses global database imports (e.g., `from services.backend.firestore import db`) which hurts testability and coupling. We should inject the db client using `Depends()`.
2. **SSE Keepalive handling**
   - **File:** `cmd/backend/run_backend.py`
   - **Effort:** S
   - **Why:** The `/audit/stream` generator hangs indefinitely if the client disconnects or if the proxy drops idle connections. We need a timeout and ping mechanism.
3. **Implement structured JSON logging**
   - **File:** `cmd/backend/run_backend.py`, `packages/aegis/agent/gate.py`
   - **Effort:** M
   - **Why:** Plain text logs are difficult to parse in Google Cloud Logging. Switching to JSON improves log aggregation.
4. **Add Request ID middleware**
   - **File:** `cmd/backend/run_backend.py`
   - **Effort:** S
   - **Why:** We lack end-to-end traceability for API requests, making debugging difficult. We should append an `X-Request-ID` to all requests.
5. **Thread executor for synchronous tools**
   - **Files:** `packages/aegis/perception/screen/ocr.py`, `packages/aegis/perception/screen/capture.py`
   - **Effort:** M
   - **Why:** CPU-bound libraries like `mss` and `rapidocr` run directly in the `asyncio` event loop in `ocr_background_loop`, stalling the entire agent process.
6. **Set max_output_tokens on Gemini calls**
   - **Files:** `packages/aegis/agent/classifier.py`, `packages/aegis/runtime/screen_executor.py`
   - **Effort:** S
   - **Why:** Omitting explicit output limits risks API cost overruns and unpredictable latency spikes.
7. **Enforce hard iteration step limit in agent loop**
   - **File:** `packages/aegis/runtime/screen_executor.py`
   - **Effort:** M
   - **Why:** The agent loop lacks a definitive hard break mechanism if `max_steps` is evaded by internal loops. We need an absolute cutoff.

---

## Phase 3 — Infrastructure & Long-Term (Highest effort, highest reward)
**Phase Goal:** Deploy broad architectural changes requiring CI/CD updates, new infrastructure (Secret Manager), test suite migrations, and Docker optimizations. These tasks require cross-team coordination.

**Phase 3 Tasks:**
1. **Expire WebAuthn Challenges Server-Side**
   - **File:** `cmd/backend/run_backend.py`
   - **Effort:** M
   - **Why:** Challenges are currently not deleted upon successful verification. Replay attacks are possible on the authorization escalation loop.
2. **Handle FCM Token Expiry**
   - **File:** `services/backend/fcm.py`
   - **Effort:** M
   - **Why:** Expiry throws raw exceptions which must be explicitly caught to remove tokens from the notification step in the authorization escalation flow.
3. **Add rate-limiting with slowapi**
   - **File:** `cmd/backend/run_backend.py`
   - **Effort:** M
   - **Why:** Protects against brute-force attacks on PINs. Changing authentication fallback speed could affect legitimate workflows.
4. **Move Secrets to Google Cloud Secret Manager**
   - **File:** `configs/backend/config.py`, `cmd/backend/run_backend.py`
   - **Effort:** L
   - **Why:** Passing API keys via standard `.env` variables is a security risk in a production containerized environment.
5. **Harden Dockerfile (Non-Root, Multi-Stage, Pinned Base)**
   - **File:** `services/backend/Dockerfile`
   - **Effort:** M
   - **Why:** The current Dockerfile runs as the `root` user and uses an unpinned base image (`python:3.11-slim`), which is a security and stability risk.
6. **Replace ad-hoc test scripts with Pytest suites**
   - **File:** `services/backend/test_backend.py`, root test scripts
   - **Effort:** L
   - **Why:** Current testing relies on an ad-hoc runner script. Pytest enables better isolation, fixture support, and mock injections for FCM/Firestore.
