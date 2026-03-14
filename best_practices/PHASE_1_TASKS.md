# Phase 1 Tasks: Critical & Safe Fixes

- **Task ID**: P1-001
- **Title**: Add global exception handler
- **File(s)**: `cmd/backend/run_backend.py`
- **Current code**:
```python
app = FastAPI(title="Aegis Backend")

# CORS Configuration
```
- **Proposed change**:
```python
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

app = FastAPI(title="Aegis Backend")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# CORS Configuration
```
- **Test**: Force an unhandled exception in an endpoint (e.g., raise `Exception("test")` in `/health`) and assert a `500` status with a sanitized JSON response. Send an invalid JSON body to `/action` and assert a `422` response.
- **Rollback**: Remove the `@app.exception_handler` decorators and functions.
- **Breaks anything?**: No. Changes only error formatting.

---

- **Task ID**: P1-002
- **Title**: Ensure CancelledError is handled properly
- **File(s)**: `packages/aegis/interfaces/ws_server.py`
- **Current code**:
```python
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"⚠️ WebSocket server error: {e}")
```
- **Proposed change**:
```python
        except asyncio.CancelledError:
            logger.info("📡 WebSocket server task cancelled.")
            raise
        except Exception as e:
            logger.error(f"⚠️ WebSocket server error: {e}")
```
- **Test**: Terminate the application gracefully (e.g., using SIGINT). Check logs to ensure `WebSocket server task cancelled` is logged and the event loop shuts down cleanly without hanging.
- **Rollback**: Change `raise` back to `pass`.
- **Breaks anything?**: No. Ensures proper task lifecycle propagation.
