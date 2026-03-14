# Aegis — Production Best Practices Guide

> Generated from codebase analysis. Tailored to the exact stack in use: FastAPI, Python 3.11, React/Vite, Firestore, Spanner, SQLAlchemy, Google GenAI/Gemini, Playwright, WebAuthn, FCM, Composio, OpenTelemetry, Docker/Nginx.

---

## Table of Contents

1. [FastAPI & Uvicorn](#1-fastapi--uvicorn)
2. [Async & Concurrency (asyncio)](#2-async--concurrency-asyncio)
3. [Firestore](#3-firestore)
4. [Cloud Spanner & SQLAlchemy](#4-cloud-spanner--sqlalchemy)
5. [SQLite / aiosqlite (Local Agent Memory)](#5-sqlite--aiosqlite-local-agent-memory)
6. [Authentication — WebAuthn & PIN](#6-authentication--webauthn--pin)
7. [AI Agent Loop (Gemini / Google GenAI)](#7-ai-agent-loop-gemini--google-genai)
8. [Computer Use — Playwright, PyAutoGUI, MSS, RapidOCR](#8-computer-use--playwright-pyautogui-mss-rapidocr)
9. [Firebase Cloud Messaging (FCM)](#9-firebase-cloud-messaging-fcm)
10. [Composio Tool Execution](#10-composio-tool-execution)
11. [Server-Sent Events (SSE)](#11-server-sent-events-sse)
12. [React & Vite Frontend](#12-react--vite-frontend)
13. [Docker & Nginx](#13-docker--nginx)
14. [OpenTelemetry & Logging](#14-opentelemetry--logging)
15. [Environment & Secrets Management](#15-environment--secrets-management)
16. [Testing](#16-testing)
17. [Cross-Cutting Concerns](#17-cross-cutting-concerns)

---

## 1. FastAPI & Uvicorn

### Dependency Injection over Global State
Use FastAPI's `Depends()` for anything shared — DB clients, config, auth context. Do not use module-level globals for mutable state.

```python
# ✅ Good
async def get_db() -> AsyncGenerator[FirestoreClient, None]:
    client = get_firestore_client()
    try:
        yield client
    finally:
        pass  # cleanup if needed

@app.get("/resource")
async def handler(db: FirestoreClient = Depends(get_db)):
    ...
```

### Always Use `lifespan` for Startup/Shutdown
You are already doing this correctly. Never use deprecated `@app.on_event("startup")` — stick with `@asynccontextmanager` lifespan.

### Use `HTTPException` with Specific Status Codes
Never return error dicts with `200 OK`. Use proper HTTP semantics:

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="User not found")
raise HTTPException(status_code=401, detail="Invalid credentials")
```

### Add a Global Exception Handler
Unhandled exceptions should never leak stack traces to clients:

```python
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
```

### Validate All Inputs with Pydantic
Every route that accepts a body must have a typed Pydantic model. Never accept raw `dict` or `Any`.

```python
class VerifyPinRequest(BaseModel):
    user_id: str
    pin: str = Field(min_length=4, max_length=12)
```

### Rate Limiting
Since this is a security-sensitive app (auth, PIN, WebAuthn), add rate limiting to sensitive endpoints using `slowapi`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/verify-pin")
@limiter.limit("5/minute")
async def verify_pin(request: Request, ...):
    ...
```

---

## 2. Async & Concurrency (asyncio)

### Never Block the Event Loop
Any blocking call inside an `async def` function will freeze ALL requests. Move blocking work to a thread pool:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

# For CPU-bound or blocking I/O
result = await asyncio.get_event_loop().run_in_executor(executor, blocking_function, arg)
```

Common offenders to watch in your stack: `PyAutoGUI`, `MSS` screen capture, `RapidOCR`, and `subprocess.Popen.wait()` — all must go through `run_in_executor`.

### Always Handle `CancelledError`
When cancelling tasks (e.g., in `stop_agent`), always re-raise `CancelledError` inside any `except Exception` block:

```python
except asyncio.CancelledError:
    raise  # Never swallow this
except Exception as e:
    logger.error(...)
```

### Avoid Long-Lived `asyncio.Queue` Leaks
For SSE streaming queues, always ensure the consumer side has a `finally` block that drains or closes the queue to prevent memory leaks when clients disconnect.

```python
async def event_generator():
    queue = asyncio.Queue()
    try:
        # produce events into queue
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=30)
            yield event
    except asyncio.TimeoutError:
        pass
    finally:
        # drain remaining items
        while not queue.empty():
            queue.get_nowait()
```

### Use `asyncio.gather` with `return_exceptions=True` for Parallel Calls
When fanning out multiple async calls, avoid letting one exception cancel the others silently:

```python
results = await asyncio.gather(
    task_a(), task_b(), task_c(),
    return_exceptions=True
)
for r in results:
    if isinstance(r, Exception):
        logger.error("Task failed: %s", r)
```

---

## 3. Firestore

### Never Call Firestore in a Tight Loop
Each `.get()` or `.set()` is a network round-trip. Batch reads and writes wherever possible:

```python
# ✅ Batch write
batch = db.batch()
for doc_ref, data in updates:
    batch.set(doc_ref, data)
await batch.commit()

# ✅ Batch read using get_all
docs = await db.get_all([ref1, ref2, ref3])
```

### Always Set Merge on Writes to Avoid Overwriting Fields
```python
# ❌ Overwrites entire document
await ref.set({"status": "active"})

# ✅ Merges only specified fields
await ref.set({"status": "active"}, merge=True)
```

### Use `.stream()` Instead of `.get()` on Large Collections
For audit logs or action history that can grow large, use async streaming instead of pulling all documents at once:

```python
async for doc in collection.stream():
    process(doc)
```

### Index Your Queries
Any query using `where()` + `order_by()` on different fields requires a composite index. Missing indexes cause silent runtime errors. Define them in `firestore.indexes.json` and deploy via Firebase CLI.

### Set Firestore Security Rules
Even though the backend is the only writer, define Security Rules to enforce that direct client access is denied for sensitive collections:

```
match /users/{userId} {
  allow read, write: if false; // server-side only
}
```

---

## 4. Cloud Spanner & SQLAlchemy

### Always Use Connection Pooling
SQLAlchemy's default pool may not be optimal for Spanner. Configure it explicitly:

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    SPANNER_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)
```

### Use Alembic for All Schema Changes — Never Mutate Schema Manually
Every schema change must go through an Alembic migration, even in development. This ensures Spanner and SQLite schemas stay in sync:

```bash
alembic revision --autogenerate -m "add_action_logs_index"
alembic upgrade head
```

### Prefer `async with session.begin()` over Manual Commit/Rollback

```python
async with async_session() as session:
    async with session.begin():
        session.add(record)
        # auto-commits on exit, auto-rolls back on exception
```

### Add Database-Level Indexes for Audit/Log Queries
For any table queried by time range (action logs, audit history), ensure there's an index on the timestamp column:

```python
class ActionLog(Base):
    __tablename__ = "action_logs"
    __table_args__ = (
        Index("ix_action_logs_created_at", "created_at"),
    )
```

---

## 5. SQLite / aiosqlite (Local Agent Memory)

### Use WAL Mode for Concurrent Reads
Write-Ahead Logging prevents read-write contention in the agent loop:

```python
async with aiosqlite.connect("memory.db") as db:
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
```

### Parameterize All Queries — No String Formatting
```python
# ❌ Never do this
await db.execute(f"SELECT * FROM memory WHERE id = '{user_id}'")

# ✅ Always use parameterized queries
await db.execute("SELECT * FROM memory WHERE id = ?", (user_id,))
```

### Run VACUUM Periodically on Long-Running Agent Sessions
SQLite can bloat over time. Schedule a periodic `VACUUM` for long-lived agent processes:

```python
await db.execute("VACUUM")
```

---

## 6. Authentication — WebAuthn & PIN

### Always Verify Challenge Server-Side and Expire It
WebAuthn challenges must be single-use. Store them in Firestore with a TTL and delete immediately on use:

```python
# On challenge generation
await db.collection("challenges").document(challenge_id).set({
    "challenge": challenge_b64,
    "user_id": user_id,
    "expires_at": datetime.utcnow() + timedelta(minutes=5),
})

# On verification — delete immediately
await challenge_ref.delete()
```

### Never Log PINs or Credentials
Audit your logging paths. Ensure no middleware, request logger, or exception handler ever logs the raw request body for PIN or WebAuthn endpoints.

```python
# Explicitly exclude sensitive routes from body logging
SENSITIVE_PATHS = {"/auth/verify-pin", "/auth/webauthn/verify"}
```

### Use Constant-Time Comparison for PIN Hashes
`bcrypt.checkpw` is already constant-time safe. Do not add any early-exit logic before calling it:

```python
import bcrypt

# ✅ Safe — always runs full comparison
is_valid = bcrypt.checkpw(pin.encode(), stored_hash)
```

### Enforce Strict WebAuthn Origin and RPID Validation
Your code uses env vars for `WEBAUTHN_RP_ID` and `ALLOWED_ORIGINS` — ensure these are strictly validated on every verification, not just registration. Never fall back to a default.

### Implement Login Attempt Throttling on PIN Endpoint
Store failed attempts in Firestore with a lockout after N failures:

```python
if attempts >= 5:
    raise HTTPException(status_code=429, detail="Account temporarily locked")
```

---

## 7. AI Agent Loop (Gemini / Google GenAI)

### Always Set `max_tokens` / `max_output_tokens`
Never call the LLM without an explicit output token cap. Uncapped responses cause unpredictable latency and cost spikes:

```python
response = await client.aio.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt,
    config=GenerateContentConfig(max_output_tokens=2048),
)
```

### Implement a Hard Iteration Cap on the Agent Loop
Prevent infinite loops with a maximum step counter:

```python
MAX_STEPS = 50

for step in range(MAX_STEPS):
    action = await agent.think(observation)
    if action.is_terminal:
        break
    observation = await execute(action)
else:
    logger.error("Agent hit max step limit — aborting")
    await notify_user("Agent loop exceeded limits")
```

### Catch and Classify LLM Errors
Gemini APIs throw different exceptions for rate limits, quota exhaustion, and model errors. Handle each distinctly:

```python
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

try:
    response = await client.generate(...)
except ResourceExhausted:
    await asyncio.sleep(60)  # backoff on quota
except ServiceUnavailable:
    logger.error("Gemini unavailable — suspending agent")
    raise
```

### Sanitize Tool Call Outputs Before Feeding Back to the Model
Never feed raw OS output (file contents, command output, OCR results) directly back as LLM context without length-capping and sanitizing:

```python
MAX_OBSERVATION_CHARS = 8000

observation = tool_result[:MAX_OBSERVATION_CHARS]
```

### Keep System Prompts in Versioned Files, Not Code
Store system prompts as `.txt` or `.md` files loaded at startup, not as inline Python strings. This makes them reviewable and diffable.

---

## 8. Computer Use — Playwright, PyAutoGUI, MSS, RapidOCR

### Run All Computer Use in a Separate Thread
`PyAutoGUI`, `mss`, and `RapidOCR` are all synchronous and CPU-bound. They must never run directly in an `async def`:

```python
async def capture_and_ocr() -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_capture_and_ocr)

def _sync_capture_and_ocr() -> str:
    screenshot = mss.mss().grab(monitor)
    result = ocr_engine.ocr(np.array(screenshot))
    return result
```

### Always Use Playwright's Async API
Do not use `sync_playwright` inside the async agent loop. Use `async_playwright` exclusively:

```python
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
```

### Set Timeouts on All Playwright Actions
Never allow Playwright to wait indefinitely. Always specify timeouts:

```python
await page.click("button#submit", timeout=5000)   # 5s
await page.wait_for_selector(".result", timeout=10000)  # 10s
```

### Implement Coordinate Validation Before PyAutoGUI Actions
Before clicking or typing at screen coordinates, validate they are within monitor bounds:

```python
def safe_click(x: int, y: int, screen_w: int, screen_h: int):
    if not (0 <= x <= screen_w and 0 <= y <= screen_h):
        raise ValueError(f"Coordinates ({x}, {y}) out of screen bounds")
    pyautogui.click(x, y)
```

### Implement a Screenshot Rate Limit in the Agent Loop
Uncapped screen captures can cause high CPU/memory usage. Enforce a minimum interval:

```python
MIN_CAPTURE_INTERVAL = 0.5  # seconds

last_capture = 0.0

async def throttled_capture():
    global last_capture
    now = time.monotonic()
    if now - last_capture < MIN_CAPTURE_INTERVAL:
        await asyncio.sleep(MIN_CAPTURE_INTERVAL - (now - last_capture))
    last_capture = time.monotonic()
    return await capture()
```

---

## 9. Firebase Cloud Messaging (FCM)

### Always Handle FCM Token Expiry
FCM tokens expire or become invalid. Handle `UnregisteredError` and clean up stale tokens from Firestore:

```python
from firebase_admin.exceptions import UnregisteredError

try:
    messaging.send(message)
except UnregisteredError:
    logger.warning("Stale FCM token for user %s — removing", user_id)
    await remove_fcm_token(user_id)
```

### Set a TTL on Auth Challenge Notifications
FCM messages can be delayed. Set a TTL matching your challenge expiry so stale push notifications don't arrive after the challenge has expired:

```python
message = messaging.Message(
    token=fcm_token,
    android=messaging.AndroidConfig(ttl=timedelta(minutes=5)),
    apns=messaging.APNSConfig(
        headers={"apns-expiration": str(int(time.time()) + 300)}
    ),
)
```

### Do Not Block the Agent Loop on FCM Delivery
Fire the FCM notification asynchronously and then poll or use a separate mechanism for the approval response. Never `await` FCM delivery confirmation inside the authorization escalation loop.

---

## 10. Composio Tool Execution

### Validate Tool Results Before Acting
Never trust Composio tool return values as ground truth. Always validate the structure before the agent uses the result:

```python
result = await composio.execute(tool_name, params)

if not result or result.get("status") != "success":
    logger.error("Tool %s returned unexpected result: %s", tool_name, result)
    raise AgentToolError(f"Tool execution failed: {tool_name}")
```

### Set Execution Timeouts on All Tool Calls
Composio tools calling external APIs can hang. Wrap all calls with `asyncio.wait_for`:

```python
try:
    result = await asyncio.wait_for(
        composio.execute(tool_name, params),
        timeout=30.0
    )
except asyncio.TimeoutError:
    logger.error("Tool %s timed out", tool_name)
    raise
```

### Audit-Log Every Tool Execution
Before and after every Composio tool call, write to your action log in Firestore. This is your audit trail for the authorization escalation flow:

```python
await log_action(user_id, tool_name, params, status="pending")
result = await composio.execute(tool_name, params)
await log_action(user_id, tool_name, params, status="completed", result=result)
```

---

## 11. Server-Sent Events (SSE)

### Always Handle Client Disconnects
When an SSE client disconnects, the generator must stop and release resources. Use `request.is_disconnected()`:

```python
from sse_starlette.sse import EventSourceResponse

async def audit_stream(request: Request):
    async def generator():
        async for event in get_audit_events():
            if await request.is_disconnected():
                break
            yield {"data": event}
    return EventSourceResponse(generator())
```

### Add a Keepalive Ping
Long-lived SSE connections will be dropped by proxies and load balancers after idle periods. Send a periodic comment ping:

```python
async def generator():
    while True:
        event = await asyncio.wait_for(queue.get(), timeout=25)
        if event is None:
            yield {"comment": "keepalive"}  # SSE comment, ignored by clients
        else:
            yield {"data": json.dumps(event)}
```

### Set Response Headers for Proxy Compatibility
```python
return EventSourceResponse(
    generator(),
    headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # disables Nginx buffering for SSE
    }
)
```

---

## 12. React & Vite Frontend

### Never Store Sensitive Data in `localStorage`
`localStorage` is readable by any JS on the page. Do not store tokens, session IDs, or user credentials there. Use `httpOnly` cookies for auth tokens, or keep them in React state for in-memory-only access.

### Use `AbortController` for All Fetch / API Calls
Prevent stale requests from updating state after a component unmounts:

```javascript
useEffect(() => {
  const controller = new AbortController();

  fetchData({ signal: controller.signal }).then(setData);

  return () => controller.abort();
}, []);
```

### Lazy-Load Heavy Routes
Playwright, OCR, and agent-related UI views should be lazily loaded to keep initial bundle size small:

```javascript
const AgentView = React.lazy(() => import('./views/AgentView'));
```

### Use Environment Variables via `import.meta.env`
Never hardcode API base URLs or backend ports. Use Vite's env system:

```javascript
// .env.local
VITE_API_BASE_URL=http://localhost:8000

// usage
const api = import.meta.env.VITE_API_BASE_URL;
```

### Enable Vite Build Optimizations for Production
In `vite.config.ts`, ensure chunking and minification are configured:

```javascript
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        vendor: ['react', 'react-dom'],
        auth: ['@simplewebauthn/browser'],
      },
    },
  },
  minify: 'esbuild',
  sourcemap: false, // disable in production
}
```

---

## 13. Docker & Nginx

### Never Run Containers as Root
Add a non-root user to your Dockerfiles:

```dockerfile
RUN addgroup --system app && adduser --system --ingroup app app
USER app
```

### Pin Base Image Versions
Never use `latest` tags in production Dockerfiles. Pin exact digest or version:

```dockerfile
# ❌ Fragile
FROM python:3.11-slim

# ✅ Pinned
FROM python:3.11.9-slim-bookworm
```

### Use Multi-Stage Builds to Minimize Image Size
You are already doing this for frontends. Apply the same pattern to the Python backend:

```dockerfile
# Build stage
FROM python:3.11.9-slim-bookworm AS builder
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11.9-slim-bookworm
COPY --from=builder /root/.local /root/.local
COPY . /app
```

### Configure Nginx for Security Headers
Add security headers in your `nginx.conf`:

```nginx
add_header X-Frame-Options "DENY";
add_header X-Content-Type-Options "nosniff";
add_header Referrer-Policy "strict-origin-when-cross-origin";
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()";
add_header Content-Security-Policy "default-src 'self'; script-src 'self'";
```

### Enable Nginx Gzip Compression for Frontend Assets

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml;
gzip_min_length 1024;
```

---

## 14. OpenTelemetry & Logging

### Attach `trace_id` to Every Log Line
With OpenTelemetry active, enrich log records with the current trace context so logs can be correlated to traces in Cloud Monitoring:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def get_trace_id() -> str:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    return format(ctx.trace_id, '032x') if ctx.is_valid else "no-trace"

logger.info("Processing request | trace_id=%s", get_trace_id())
```

### Never Log PII or Secrets
Implement a log filter that scrubs sensitive fields before they reach Cloud Logging:

```python
class SensitiveFilter(logging.Filter):
    SCRUB_KEYS = {"pin", "password", "token", "credential", "challenge"}

    def filter(self, record):
        if isinstance(record.args, dict):
            record.args = {
                k: "***" if k in self.SCRUB_KEYS else v
                for k, v in record.args.items()
            }
        return True

logger.addFilter(SensitiveFilter())
```

### Use Structured Logging (JSON) in Production
Plain text logs are hard to query in Cloud Logging. Emit JSON:

```python
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.formatTime(record),
        })
```

### Create Metrics for Agent Loop Telemetry
Track key agent events as custom metrics via OpenTelemetry:

```python
from opentelemetry import metrics

meter = metrics.get_meter("aegis.agent")
steps_counter = meter.create_counter("agent.steps")
tool_calls_counter = meter.create_counter("agent.tool_calls")

# Inside the loop
steps_counter.add(1, {"agent_id": agent_id})
```

---

## 15. Environment & Secrets Management

### Use Secret Manager Instead of `.env` for Production Credentials
`.env` files on disk are a security risk in containerized deployments. Use Google Cloud Secret Manager:

```python
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    return client.access_secret_version(name=name).payload.data.decode()
```

Keep `.env` only for local development and ensure `.env` is in `.gitignore`.

### Fail Fast on Missing Config at Startup
Never let a missing env variable cause a silent failure deep in a request path:

```python
import os

def require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Required environment variable '{key}' is not set")
    return value

WEBAUTHN_RP_ID = require_env("WEBAUTHN_RP_ID")
BACKEND_URL = require_env("BACKEND_URL")
```

### Never Commit Secrets to Version Control
Ensure your `.gitignore` covers all secret files:

```gitignore
.env
.env.*
*.pem
*.key
service-account.json
firebase-adminsdk*.json
```

---

## 16. Testing

### Replace Ad-Hoc Scripts with Proper Pytest Test Cases
`testOCR.py` and `test_backend.py` style scripts are not repeatable in CI. Move them to `pytest` with proper fixtures:

```python
# tests/test_backend.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
```

### Mock FCM and Gemini Calls in Tests
Never hit external APIs in unit or integration tests:

```python
@pytest.fixture
def mock_fcm(monkeypatch):
    monkeypatch.setattr("firebase_admin.messaging.send", lambda m: "mock-message-id")

@pytest.fixture
def mock_gemini(monkeypatch):
    monkeypatch.setattr("google.genai.Client.generate", AsyncMock(return_value=...))
```

### Test the Authorization Escalation Loop Explicitly
This is the most critical flow in the system. It should have dedicated tests covering: agent suspends → FCM fires → biometric approved → agent resumes, and the rejection path.

### Add Coverage Enforcement to CI
```bash
pytest --cov=. --cov-fail-under=70
```

Start at 70% and raise the threshold over time.

---

## 17. Cross-Cutting Concerns

### Request ID Middleware
Add a `X-Request-ID` to every request for end-to-end traceability across services:

```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestIDMiddleware)
```

### Idempotency for Critical Writes
For action logs and auth events written to Firestore, use deterministic document IDs (e.g., hash of `user_id + timestamp + action`) to prevent duplicate writes on retries.

### Implement Circuit Breakers for External Dependencies
If Gemini, Composio, or Firestore are unavailable, the agent should degrade gracefully rather than hammering a failing service:

```python
# Using the `circuitbreaker` library
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_gemini(prompt):
    return await client.generate(prompt)
```

### Health Check Should Verify Dependencies
Your current `/health` returns `{"status": "ok"}` unconditionally. For a real liveness/readiness check, probe actual dependencies:

```python
@app.get("/health")
async def health(db: FirestoreClient = Depends(get_db)):
    try:
        await db.collection("_health").document("ping").get()
        return {"status": "ok", "firestore": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "degraded", "error": str(e)})
```

---

*Document generated from static codebase analysis. Revisit after any major dependency upgrade or architectural change.*