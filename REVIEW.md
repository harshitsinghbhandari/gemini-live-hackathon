# Aegis — Full Code Review
Date: 2025-03-05
Files reviewed: 68
Total issues found: 24

## Summary
The Aegis project is a sophisticated multi-platform AI agent with a solid architectural foundation. However, it currently suffers from critical integration failures between the Python agent and the Swift applications due to mismatched JSON schemas and inconsistent backend URLs. While the core logic is sound, these "last-mile" connectivity issues will prevent the demo from working end-to-end.

## Category 1 — BROKEN (8 issues)

### BROKEN-001
**File:** `AegisApp_Mac/AegisApp/WebSocketClient.swift` (Lines 81-86)
**Issue:** `YellowConfirmRequest` decoding fails. Python sends `speak` and `id`, but Swift expects `question` and `id`. Also, `tool` and `toolkit` are missing from the Python payload.
**Impact:** YELLOW tier actions will never trigger the confirmation UI in the Mac app.
**Fix:** Align `aegis/gate.py` broadcast payload with `YellowConfirmRequest` struct.

### BROKEN-002
**File:** `AegisApp_Mac/AegisApp/WebSocketClient.swift` (Lines 88-100)
**Issue:** `RedAuthRequest` decoding fails. Python sends `request_id` and `speak`, but Swift expects `id` and `reason`. `tool` and `toolkit` are also missing.
**Impact:** RED tier actions will never trigger the "Check your iPhone" UI on Mac.
**Fix:** Align `aegis/gate.py` broadcast payload with `RedAuthRequest` struct.

### BROKEN-003
**File:** `AegisApp_iOS/AegisApp_iOS/AegisIOSViewModel.swift` (Line 16)
**Issue:** `baseURL` is hardcoded to an old GCP URL (`https://guardian-backend-1090554066699.us-central1.run.app`).
**Impact:** iOS app will poll the wrong backend and never see auth requests or session updates.
**Fix:** Change to `https://apiaegis.projectalpha.in`.

### BROKEN-004
**File:** `AegisApp_iOS/AegisApp_iOS/FirestoreClient.swift` (Lines 22-43)
**Issue:** `ActionCard` decoding in iOS fails because `timestamp` is often a Firestore `Timestamp` object, but `JSONDecoder` expects an ISO8601 string.
**Impact:** The MirrorView on iOS will remain empty.
**Fix:** Implement custom `Date` decoding logic or pre-process the dictionary before `JSONSerialization`.

### BROKEN-005
**File:** `AegisApp_iOS/AegisApp_iOS/AegisApp_iOSApp.swift` (Line 42)
**Issue:** `registerTokenWithBackend` uses a different URL than the ViewModel.
**Impact:** Device registration might hit the correct backend while the rest of the app hits the wrong one.
**Fix:** Centralize URL configuration in a config file.

### BROKEN-006
**File:** `aegis/voice.py` (Line 210)
**Issue:** `_check_remote_stop` polls `GET /session/status` without a `DEVICE_ID`.
**Impact:** If multiple users were on the platform, any session stop would kill all active agents globally.
**Fix:** Add `?device_id=` parameter to the status check.

### BROKEN-007
**File:** `AegisApp_Mac/AegisApp/WebSocketClient.swift` (Lines 113-120)
**Issue:** `waveform` event expects a `Float` but the broadcast sends a `Float`. However, the `waveformPublisher` is defined as `[Float]`.
**Impact:** Waveform animation might not drive correctly if the array conversion is janky.
**Fix:** Ensure `ws_server.py` sends an array or `WebSocketClient` consistently wraps the single float into an array.

### BROKEN-008
**File:** `AegisApp_iOS/AegisApp_iOS/Info.plist`
**Issue:** Missing `NSFaceIDUsageDescription`.
**Impact:** iOS app will crash the first time it attempts to use Face ID for RED auth.
**Fix:** Add `NSFaceIDUsageDescription` to `Info.plist`.

## Category 2 — WRONG (4 issues)

### WRONG-001
**File:** `aegis/gate.py` (Line 144)
**Issue:** `toolkit` is derived by splitting the tool name, but if `tool` is `None` (on classification failure), it will crash.
**Impact:** Agent crash during error handling.
**Fix:** Add null check for `tool` before splitting.

### WRONG-002
**File:** `dashboard/src/components/AgentStatus.jsx` (Line 27)
**Issue:** Hardcoded "Harshit's MacBook" in the UI.
**Impact:** Poor UX for other users/judges.
**Fix:** Pass `device` ID from the `lastEntry` metadata.

### WRONG-003
**File:** `aegis/classifier.py` (Line 36)
**Issue:** `GMAIL_FETCH_EMAILS` mapping in prompt includes `label_ids: ["INBOX"]`, but Composio might expect a different format or no label.
**Impact:** Tool execution might fail due to strict argument validation.
**Fix:** Verify Composio Gmail tool schema and update prompt.

### WRONG-004
**File:** `backend/main.py` (Line 51)
**Issue:** Auto-deny logic uses `datetime.now(datetime.timezone.utc)` but `created_at` from Firestore might be naive or different format.
**Impact:** Premature or delayed auto-denial.
**Fix:** Ensure consistent timezone-aware comparisons.

## Category 3 — MISSING (4 issues)

### MISSING-001
**File:** `AegisApp_Mac/AegisApp/AegisMacViewModel.swift` (Line 92)
**Issue:** `DEVICE_ID` is hardcoded as "harshit-macbook" instead of reading from a config or Keychain.
**Impact:** Difficult to test on different machines.
**Fix:** Move to a configurable constant or Keychain entry.

### MISSING-002
**File:** `AegisApp_iOS/AegisApp_iOS/MirrorView.swift`
**Issue:** No real-time waveform animation in the iOS Mirror view.
**Impact:** iOS experience feels "static" compared to the Mac app.
**Fix:** Sync waveform peak value to Firestore or use a lightweight WebSocket proxy.

### MISSING-003
**File:** `aegis/ws_server.py`
**Issue:** No reconnection logic in the `websockets.serve` context if the server fails to bind.
**Impact:** If port 8765 is occupied, the agent starts but the UI stays disconnected.
**Fix:** Add try-except around server start with retry logic.

### MISSING-004
**File:** `backend/main.py`
**Issue:** `/session/status` (GET) does not filter by device.
**Impact:** Global session state shared across all users.
**Fix:** Add device-specific session documents in Firestore.

## Category 4 — FRAGILE (3 issues)

### FRAGILE-001
**File:** `AegisApp_Mac/AegisApp/WebSocketClient.swift` (Lines 126-130)
**Issue:** `scheduleReconnect` uses a fixed 3s timer without exponential backoff.
**Impact:** High CPU usage if the agent is down for a long time.
**Fix:** Implement simple exponential backoff (3s, 6s, 12s...).

### FRAGILE-002
**File:** `aegis/auth.py` (Lines 21-23)
**Issue:** `objc` import failure only logged once. If a user installs `pyobjc` later, they must restart the agent.
**Impact:** Minor, but annoying for dev setup.
**Fix:** No immediate fix needed, but improve error message to suggest `pip install pyobjc`.

### FRAGILE-003
**File:** `backend/firestore.py` (Lines 52-67)
**Issue:** `listen_to_audit_log` uses a synchronous `on_snapshot` listener inside an async FastAPI environment.
**Impact:** Risk of blocking the event loop under high load.
**Fix:** Move the listener to a dedicated thread or use a purely async polling approach if throughput is low.

## Category 5 — POLISH (2 issues)

### POLISH-001
**File:** `aegis_menubar.py` (Line 115)
**Issue:** `status == "blocked"` uses `ICON_ERROR` instead of a dedicated "blocked" or "auth failed" icon.
**Impact:** Confusing UX; users might think the app crashed.
**Fix:** Use `ICON_AUTH` or a yellow warning icon.

### POLISH-002
**File:** `AegisApp_Mac/AegisApp/RedAuthView.swift`
**Issue:** Progress bar for 30s timeout is linear and doesn't account for network latency in polling.
**Impact:** The Mac UI might time out before the backend actually denies the request.
**Fix:** Sync timer more closely with backend `created_at`.

## Category 6 — Dormant (3 issues)

### DORMANT-001
**File:** `components/` (Directory)
**Issue:** Contains old versions of the core logic now found in `aegis/`.
**Impact:** Confusion for new developers; potential to edit the wrong file.
**Fix:** Delete the `components/` directory.

### DORMANT-002
**File:** `voice_agent.py` (File)
**Issue:** Redundant copy of the voice agent logic.
**Impact:** Clutters root directory.
**Fix:** Delete `voice_agent.py`.

### DORMANT-003
**File:** `generative-ai/` (Directory)
**Issue:** Empty directory.
**Impact:** Clutter.
**Fix:** Delete.

## Priority Fix Order
1. **BROKEN-001 & BROKEN-002:** Fix JSON schema mismatches. Without this, the Mac App is just a shell.
2. **BROKEN-003:** Fix backend URL in iOS. Essential for remote auth demo.
3. **BROKEN-008:** Add `NSFaceIDUsageDescription`. App will crash on demo otherwise.
4. **BROKEN-004:** Fix Firestore Date decoding. Required for iOS Mirror view.
5. **WRONG-001:** Fix potential crash in `gate.py`.

## Estimated Fix Time
| Category | Issues | Est. Time |
|----------|--------|-----------|
| BROKEN   | 8      | 4 hours   |
| WRONG    | 4      | 2 hours   |
| MISSING  | 4      | 3 hours   |
| FRAGILE  | 3      | 1.5 hours |
| POLISH   | 2      | 1 hour    |
| DORMANT  | 3      | 0.5 hours |
| **Total**| 24     | 12 hours  |
