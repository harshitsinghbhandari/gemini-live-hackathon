# Phase 2 Tasks: Structural Improvements

- **Task ID**: P2-001
- **Title**: Add Dependency Injection for Firestore
- **File(s)**: `cmd/backend/run_backend.py`
- **Current code**:
```python
from services.backend.firestore import db

# ... used directly inside endpoints like:
        docs = db.collection("users").document(user_id).collection("auth_requests")\
```
- **Proposed change**:
```python
from google.cloud.firestore import AsyncClient

async def get_db() -> AsyncClient:
    from services.backend.firestore import db
    return db

# Update endpoint definitions:
@app.get("/auth/pending")
async def get_pending_auth(device: str = None, user_id: str = Depends(get_user_id), db: AsyncClient = Depends(get_db)):
    try:
        docs = db.collection("users").document(user_id).collection("auth_requests")\
```
- **Test**: Hit `/auth/pending` with valid credentials. Verify it fetches from the DB correctly without runtime errors.
- **Rollback**: Revert `Depends(get_db)` parameters back to the global `db` import.
- **Breaks anything?**: No external changes; merely internal DI structure.

---

- **Task ID**: P2-002
- **Title**: SSE Keepalive handling
- **File(s)**: `cmd/backend/run_backend.py`
- **Current code**:
```python
        try:
            while True:
                if await request.is_disconnected():
                    break
                data = await queue.get()
                yield {
                    "data": json.dumps(data, default=str)
                }
        finally:
```
- **Proposed change**:
```python
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield {"data": json.dumps(data, default=str)}
                except asyncio.TimeoutError:
                    yield {"comment": "keepalive"}
        finally:
```
- **Test**: Connect to `/audit/stream`. Wait 30 seconds without triggering any agent actions. Ensure a keepalive comment `(:keepalive)` is received by the client.
- **Rollback**: Remove `asyncio.wait_for` and return to a blocking `queue.get()`.
- **Breaks anything?**: No.

---

- **Task ID**: P2-003
- **Title**: Implement structured JSON logging
- **File(s)**: `cmd/backend/run_backend.py`, `packages/aegis/agent/gate.py`
- **Current code**:
```python
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```
- **Proposed change**:
```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.formatTime(record),
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)
```
- **Test**: Start the backend process. Output in the terminal should be JSON dictionaries instead of plain text lines.
- **Rollback**: Revert `logging.basicConfig` to defaults.
- **Breaks anything?**: Log parsing tooling may need adjustments.

---

- **Task ID**: P2-004
- **Title**: Add Request ID middleware
- **File(s)**: `cmd/backend/run_backend.py`
- **Current code**:
```python
app.add_middleware(
    CORSMiddleware,
    # ...
)
```
- **Proposed change**:
```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestIDMiddleware)
```
- **Test**: Make a standard HTTP GET request. The response headers must contain `X-Request-ID`.
- **Rollback**: Remove `RequestIDMiddleware` class and `app.add_middleware()`.
- **Breaks anything?**: No.

---

- **Task ID**: P2-005
- **Title**: Thread executor for synchronous tools
- **File(s)**: `packages/aegis/perception/screen/ocr.py`, `packages/aegis/perception/screen/capture.py`
- **Current code**:
```python
async def ocr_background_loop(context) -> None:
    # ...
            loop_start = time.time()
            result = await asyncio.to_thread(_process_frame, context)
```
- **Proposed change**:
```python
import concurrent.futures

ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

async def ocr_background_loop(context) -> None:
    # ...
            loop_start = time.time()
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(ocr_executor, _process_frame, context)
```
- **Test**: Start the agent. Ensure the voice response stream is not significantly degraded while OCR captures in the background.
- **Rollback**: Revert `run_in_executor` back to `asyncio.to_thread`.
- **Breaks anything?**: Thread pooling reduces generic asyncio.to_thread overhead, but shouldn't break functionality.

---

- **Task ID**: P2-006
- **Title**: Set max_output_tokens on Gemini calls
- **File(s)**: `packages/aegis/agent/classifier.py`, `packages/aegis/runtime/screen_executor.py`
- **Current code**:
```python
        response = await client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[prompt_text],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
```
- **Proposed change**:
```python
        response = await client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[prompt_text],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=1024
            )
        )
```
- **Test**: Trigger the classifier by requesting a RED tier action. Ensure it responds without error and classifies the payload successfully.
- **Rollback**: Remove the `max_output_tokens=1024` kwarg.
- **Breaks anything?**: Could truncate exceptionally long reasoning logs.

---

- **Task ID**: P2-007
- **Title**: Enforce hard iteration step limit in agent loop
- **File(s)**: `packages/aegis/runtime/screen_executor.py`
- **Current code**:
```python
    for step in range(max_steps):
        response = await client.aio.models.generate_content(
```
- **Proposed change**:
```python
    HARD_MAX_STEPS = 50
    for step in range(min(max_steps, HARD_MAX_STEPS)):
        response = await client.aio.models.generate_content(
```
- **Test**: Set `max_steps` to 100 via tool args and ensure the loop breaks after 50.
- **Rollback**: Remove `min(max_steps, HARD_MAX_STEPS)`.
- **Breaks anything?**: Stops infinitely looping agents from exhausting quota.
