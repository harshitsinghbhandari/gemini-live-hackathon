# Risk Register

| Practice | File(s) Affected | Risk Level | Risk Reason | Recommendation |
|---|---|---|---|---|
| Dependency Injection for Shared Resources | `cmd/backend/run_backend.py` | LOW | Current backend uses global `db` imports which hurts testability. Changing to `Depends(get_db)` is safe. | Implement in Phase 2 |
| Global Exception Handler | `cmd/backend/run_backend.py` | LOW | Prevents raw stack traces from reaching clients. No API changes. | Implement in Phase 1 |
| Handle `CancelledError` Properly | `packages/aegis/interfaces/ws_server.py` | LOW | Silent consumption of `CancelledError` can cause unpredictable task states on shutdown. | Implement in Phase 1 |
| Rate Limiting on Auth/PIN | `cmd/backend/run_backend.py` | HIGH | Protects against brute-force attacks on PINs. Changing authentication fallback speed could affect legitimate workflows. Must not remove the fallback. | Implement in Phase 3 |
| Expire WebAuthn Challenges Server-Side | `cmd/backend/run_backend.py` | HIGH | Modifies the authorization escalation loop logic. While necessary, it must be rolled out carefully to prevent lockouts. | Implement in Phase 3 |
| Handle FCM Token Expiry | `services/backend/fcm.py` | HIGH | Directly alters the notification step in the authorization escalation flow. Requires a dedicated rollback plan. | Implement in Phase 3 |
| Input Validation with Pydantic | `cmd/backend/run_backend.py` | LOW | Most routes already use Pydantic models (e.g., `ActionLog`, `AuthRequest`), but strict typing is needed. | Implement in Phase 2 |
| ThreadPoolExecutor for Sync UI/Screen Calls | `packages/aegis/perception/screen/ocr.py`, `packages/aegis/perception/screen/capture.py` | HIGH | `mss` and `RapidOCR` currently run blocking code inside `asyncio` loops. Modifying the agent loop structure is high risk. | Implement in Phase 2 |
| Batch Firestore Queries & Writes | `services/backend/firestore.py` | LOW | Many isolated `.set()` and `.update()` calls. Can easily be converted to batches. | Implement in Phase 2 |
| Alembic Migrations for Cloud Spanner/SQLite | N/A | DO-NOT-IMPLEMENT | The current application relies on Firestore, not Spanner/SQLAlchemy. | N/A |
| Set `max_output_tokens` in LLM Calls | `packages/aegis/agent/classifier.py`, `packages/aegis/runtime/screen_executor.py` | MEDIUM | Without token limits, cost overruns occur. Touches AI logic. | Implement in Phase 2 |
| Hard Step Cap on Agent Loop | `packages/aegis/runtime/screen_executor.py` | MEDIUM | Explicit `max_steps` needs rigid enforcement. Touches AI logic. | Implement in Phase 2 |
| Non-Blocking Agent Loop for FCM | `packages/aegis/agent/gate.py`, `services/backend/fcm.py` | DO-NOT-IMPLEMENT | The current loop explicitly polls the backend to keep the agent suspended during auth escalation. Modifying this could break the state machine. | Leave as-is |
| Validate Composio Tool Results | `packages/aegis/agent/gate.py` | DO-NOT-IMPLEMENT | Native computer use via `screen_executor.py` bypasses Composio. | Leave as-is |
| SSE Keepalive & Disconnects | `cmd/backend/run_backend.py` | LOW | `audit_stream` lacks a proper keep-alive ping for long-lived proxy connections. | Implement in Phase 2 |
| Pin Docker Base Images & Non-Root | `services/backend/Dockerfile` | LOW | Dockerfile currently uses `python:3.11-slim` (unpinned) and runs as root. | Implement in Phase 3 |
| OpenTelemetry & JSON Logging | `cmd/backend/run_backend.py` | MEDIUM | Traces are critical for identifying latency in the vision-to-speech loop. | Implement in Phase 2/3 |
| Move Secrets to Secret Manager | `cmd/backend/run_backend.py` | LOW | Secrets are currently pulled directly via `os.environ.get`. | Implement in Phase 3 |
| Pytest Test Cases | `services/backend/test_backend.py` | LOW | Current tests are basic and don't mock FCM cleanly. | Implement in Phase 3 |

### High Risk / Do Not Implement Justifications

**Authorization Escalation Loop Tasks (HIGH Risk)**
`Expire WebAuthn Challenges`, `Handle FCM Token Expiry`, and `Rate Limiting on Auth/PIN` directly impact the most sensitive flow (agent suspends → FCM push → biometric approval → agent resumes). They are marked HIGH RISK and must only be deployed during Phase 3 with robust testing to prevent user lockout.

**ThreadPoolExecutor for Sync UI/Screen Calls (HIGH Risk)**
`mss` and `RapidOCR` are currently deeply integrated into the `asyncio` event loops. Modifying this touches core computer use logic and could break timing synchronization with the Gemini Live API. Relegated to Phase 2.

**Non-Blocking Agent Loop for FCM (DO-NOT-IMPLEMENT)**
The agent must wait synchronously for the user to approve the red-tier request before it executes the action. `gate_action` must block while polling the `/auth/status/{request_id}` endpoint. Changing this to event-driven webhooks could break the continuous Gemini Live stream lifecycle.

**Alembic Migrations / Composio Tools (DO-NOT-IMPLEMENT)**
The stack uses Firestore strictly. Spanner and Composio tools are vestigial or reference implementations and not the critical path.
