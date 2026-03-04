# Backend Code Audit Report

**Date:** 2026-03-04  
**Scope:** `backend/` directory cross-referenced against `generated_samples/`

---

## Summary

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 Critical | 3 | Wrong Firestore client, broken references, async/sync mismatch |
| 🟡 Medium | 4 | Missing error handling, test mock misalignment, SERVER_TIMESTAMP misuse |
| 🟢 Low | 3 | Missing logging, optional model defaults, Dockerfile improvements |

---

## 🔴 Critical Issues

### 1. `firestore.py` — Wrong Firestore Client Library

**Line 1:** `from google.cloud import firestore_admin_v1`  
**Line 5:** `db = firestore_admin_v1.FirestoreAdminClient()`

The code imports `firestore_admin_v1.FirestoreAdminClient`, which is the **Admin API** for managing databases, indexes, and backups. It does **NOT** support `.collection()`, `.document()`, `.set()`, `.get()`, `.update()`, or `.on_snapshot()` — these are all methods on the high-level `google.cloud.firestore.AsyncClient`.

**Generated Samples evidence:**
- `firestore_v1_generated_firestore_admin_create_index_async.py` → uses `firestore_admin_v1.FirestoreAdminAsyncClient()` for **index management only**
- `firestore_v1_generated_firestore_create_document_async.py` → uses `firestore_v1.FirestoreAsyncClient()` for **document CRUD**

**Fix:** Replace with `google.cloud.firestore.AsyncClient()` (the idiomatic high-level SDK).

---

### 2. `firestore.py` — Broken `firestore.SERVER_TIMESTAMP` References

**Lines 14, 30:** `firestore.SERVER_TIMESTAMP`  
**Line 39:** `firestore.Query.DESCENDING`

The module never imports `firestore` as a name — only `firestore_admin_v1`. These references will raise `NameError` at runtime.

**Fix:** Import `from google.cloud import firestore` and use `firestore.SERVER_TIMESTAMP` correctly, or use the `AsyncClient`'s built-in constants.

---

### 3. `firestore.py` — Async/Sync Mismatch

**Lines 7–10, 12–18, 20–24, 26–31:** Functions are declared `async def` and use `await`, but `firestore_admin_v1.FirestoreAdminClient()` is a **synchronous** client. Even with the correct library, you must use `firestore.AsyncClient()` not `firestore.Client()` for `await` to work.

**Lines 52–55 (`get_audit_logs`):** Uses `async for doc in docs` on `query.limit(limit).stream()` — but the sync `stream()` method returns a regular iterator, not an async one.

**Generated Samples evidence:**
- All `*_async.py` samples use `firestore_v1.FirestoreAsyncClient()` — never the sync `FirestoreClient()` in async functions.

**Fix:** Use `firestore.AsyncClient()` consistently throughout.

---

## 🟡 Medium Issues

### 4. `firestore.py` — `listen_to_audit_log` Uses Sync API Pattern

**Lines 33–45:** `on_snapshot` is a sync/threaded callback pattern from the high-level SDK. The current code uses it on `firestore_admin_v1.FirestoreAdminClient()` which doesn't support this method at all.

**Fix:** Use `google.cloud.firestore.Client()` (sync) specifically for the listener since `on_snapshot` is inherently thread-based — and convert the callback data via `asyncio.Queue` (which the `main.py` already does correctly).

---

### 5. `test_backend.py` — Mock Targets Misaligned

**Line 12:** `patch("google.cloud.firestore.AsyncClient")` — but the actual backend imports `firestore_admin_v1`. The mocks patch the wrong import path, so they won't intercept the real import.

**Fix:** After fixing `firestore.py` to use the correct client, ensure test mocks match the actual import paths.

---

### 6. `fcm.py` — Firebase Init Fails Silently

**Lines 9–13:** If `firebase_admin.initialize_app()` fails, it's caught and logged as a warning. But subsequent calls to `messaging.send()` will also fail because the app was never initialized — leading to confusing double errors.

**Fix:** Track initialization state and skip FCM calls gracefully when not initialized.

---

### 7. `main.py` — SSE Stream Missing JSON Serialization

**Line 76:** The `data` from the Firestore callback is a `dict`, but SSE `EventSourceResponse` expects `data` to be a **string**. Firestore dict data containing datetime objects will fail JSON serialization.

**Fix:** Serialize explicitly with `json.dumps(data, default=str)`.

---

## 🟢 Low Issues

### 8. `models.py` — Optional Fields Missing Defaults

**Lines 9, 16:** `tool` and `error` are `Optional[str]` but have no `= None` default. This means they are **required** in requests even though they're typed as optional.

**Fix:** Add `= None` defaults.

---

### 9. `config.py` — No Logging Setup

No logging configuration is set up anywhere in the backend. `fcm.py` uses `logging.getLogger(__name__)` but there's no handler configured, so log messages are silently dropped.

**Fix:** Add basic logging config in `config.py` or `main.py`.

---

### 10. `Dockerfile` — No `.dockerignore`, No Health Check

The `COPY . .` copies everything including `__pycache__`, `.env`, and test files into the production image.

**Fix:** Add a `.dockerignore` file and consider a `HEALTHCHECK` instruction.

---

## Cross-Reference Matrix

| Backend Operation | Correct Sample | Backend Used | Match? |
|---|---|---|---|
| Create document | `firestore_v1.FirestoreAsyncClient()` | `firestore_admin_v1.FirestoreAdminClient()` | ❌ |
| Get document | `firestore_v1.FirestoreAsyncClient()` | `firestore_admin_v1.FirestoreAdminClient()` | ❌ |
| Update document | `firestore_v1.FirestoreAsyncClient()` | `firestore_admin_v1.FirestoreAdminClient()` | ❌ |
| Query/List documents | `firestore_v1.FirestoreAsyncClient()` | `firestore_admin_v1.FirestoreAdminClient()` | ❌ |
| Listen (snapshot) | `firestore_v1.FirestoreAsyncClient()` | `firestore_admin_v1.FirestoreAdminClient()` | ❌ |
| Admin (indexes, backups) | `firestore_admin_v1.FirestoreAdminAsyncClient()` | N/A (not needed) | ✅ |

---

## Files Changed

| File | Changes |
|------|---------|
| `firestore.py` | Complete rewrite — correct client, proper async, fix SERVER_TIMESTAMP |
| `main.py` | Add JSON serialization for SSE, add logging config |
| `models.py` | Add `= None` defaults for optional fields |
| `fcm.py` | Track Firebase init state, skip calls when not initialized |
| `test_backend.py` | Align mock paths with corrected imports |
