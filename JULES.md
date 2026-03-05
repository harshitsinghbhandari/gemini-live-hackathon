# Aegis — Jules Agent Prompt

---

## Your First Step — Read Before Writing Anything

Before writing a single line of Swift, read these files in order:

1. `aegis/ws_server.py` — exact WebSocket event schemas, every event type and payload shape
2. `aegis/config.py` — all constants, URLs, device IDs
3. `aegis/classifier.py` — tier levels (GREEN/YELLOW/RED) and how they are determined
4. `aegis/gate.py` — the orchestration flow: classify → auth → execute
5. `aegis/executor.py` — what gets sent back after execution
6. `backend/main.py` — every API endpoint, exact request/response shapes
7. `backend/models.py` — Pydantic models (these become your Swift Codable structs exactly)
8. `Stitch/` — UI reference screens. Use ONLY as visual reference for layout and color. Do NOT copy any logic or state from them. All state comes from live backend data.

Do not assume anything. Read the actual code.

---

## What You Are Building

Two separate native SwiftUI apps:

- `AegisApp_mac/` — macOS app, connects to the Python agent via WebSocket on `ws://localhost:8765`
- `AegisApp_ios/` — iOS app, connects to GCP backend via Firestore real-time listener + FCM push notifications

Both apps share the same design language. Both consume live data only. No mock data, no placeholder states, no dummy actions anywhere in the codebase.

---

## Absolute Rules — Violations Will Break the App

- **NO dummy data. NO mock data. NO hardcoded action lists. NO placeholder states.** Every piece of data shown in the UI must come from a live source: WebSocket, Firestore, or the GCP API.
- **NO UIKit. NO AppKit directly.** SwiftUI only.
- **NO third-party dependencies** except Firebase iOS SDK (Firestore + FCM).
- **`@MainActor`** on every ViewModel.
- **Never block the main thread.** All network, WebSocket, and Firestore work on background tasks/actors.
- **Dark mode only.** No light mode.
- **API keys in Keychain only.** Never hardcoded, never in UserDefaults.
- **Every view must compile and run.** No TODO stubs that crash. If a feature is not yet wired, show a real empty state from actual data being empty — not a fake placeholder.
- **Build must succeed with zero warnings.**
- **Test on macOS 14+ and iOS 17+.**

---

## Shared Design Language

```
Background:     #0a0a0f  (near black)
Accent purple:  #7c3aed
Green tier:     #16a34a
Yellow tier:    #ca8a04
Red tier:       #dc2626
Font:           SF Pro (system default)
```

Reference `Stitch/` folder for exact layout proportions and visual hierarchy. Implement everything in native SwiftUI — not HTML, not WebView.

---

## Shared Swift Models

Derive these EXACTLY from `backend/models.py` and `aegis/ws_server.py`. If the backend shape changes, these change too.

### `ActionCard.swift`

```swift
struct ActionCard: Identifiable, Codable, Equatable {
    let id: String
    let timestamp: Date
    let action: String
    let tier: TierLevel
    let tool: String
    let toolkit: String
    let reason: String
    let upgraded: Bool
    let speak: String
    let authUsed: Bool
    let blocked: Bool
    let success: Bool
    let durationMs: Int

    enum TierLevel: String, Codable {
        case green  = "GREEN"
        case yellow = "YELLOW"
        case red    = "RED"

        var color: Color {
            switch self {
            case .green:  return Color(hex: "16a34a")
            case .yellow: return Color(hex: "ca8a04")
            case .red:    return Color(hex: "dc2626")
            }
        }

        var icon: String {
            switch self {
            case .green:  return "checkmark.circle.fill"
            case .yellow: return "exclamationmark.circle.fill"
            case .red:    return "lock.shield.fill"
            }
        }
    }
}
```

### `AgentStatus.swift`

```swift
enum AgentStatus: Equatable {
    case idle
    case listening
    case executing
    case waitingAuth
    case error(String)

    var icon: String {
        switch self {
        case .idle:        return "◈"
        case .listening:   return "◉"
        case .executing:   return "◌"
        case .waitingAuth: return "⊠"
        case .error:       return "⊗"
        }
    }

    var color: Color {
        switch self {
        case .idle:        return .gray
        case .listening:   return Color(hex: "7c3aed")
        case .executing:   return .orange
        case .waitingAuth: return Color(hex: "dc2626")
        case .error:       return Color(hex: "dc2626")
        }
    }
}
```

### `RedAuthRequest.swift`

```swift
// Match exact shape from backend/models.py AuthRequest
struct RedAuthRequest: Codable, Identifiable {
    let id: String
    let action: String
    let reason: String
    let tool: String
    let toolkit: String
    let requestedAt: Date
    var expiresAt: Date  // 30 seconds from requestedAt
}
```

### `YellowConfirmRequest.swift`

```swift
// Match exact shape from ws_server.py yellow_confirm event
struct YellowConfirmRequest: Codable, Identifiable {
    let id: String
    let action: String
    let question: String  // Gemini's spoken question, e.g. "Shall I create a draft to john@...?"
    let tool: String
    let toolkit: String
}
```

---

## macOS App — `AegisApp_mac/`

### Window Configuration

```swift
// AegisMacApp.swift
@main struct AegisMacApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(width: 380, height: 680)
        }
        .windowStyle(.hiddenTitleBar)
        .windowResizability(.contentSize)
    }
}
```

Background: `#0a0a0f` with `.ultraThinMaterial` vibrancy. Rounded window corners.

---

### `WebSocketClient.swift` (macOS)

Connects to `ws://localhost:8765` — the Python agent's local WebSocket server.

```swift
// Read ws_server.py FIRST to get exact event type strings and payload shapes.
// Every event type broadcast by ws_server.py must be handled here.
// Auto-reconnect every 3 seconds on disconnect.
// Parse all events via Combine publishers on a background actor.
// Events to handle (verify names against ws_server.py):
//   "status"           → publish new AgentStatus
//   "action"           → publish new ActionCard (append to stream)
//   "yellow_confirm"   → publish YellowConfirmRequest
//   "red_auth_started" → publish RedAuthRequest
//   "red_auth_result"  → publish auth result (approved: Bool)
//   "session_started"  → clear action stream
//   "session_ended"    → mark session inactive
//   "waveform"         → publish [Float] of bar heights (0.0–1.0, count matches ws_server.py)
//
// Outgoing events:
//   "yellow_response"  → send {id, confirmed: Bool}
```

---

### `AegisMacViewModel.swift`

```swift
@MainActor
final class AegisMacViewModel: ObservableObject {
    @Published var status: AgentStatus = .idle
    @Published var actions: [ActionCard] = []          // live from WebSocket, newest first
    @Published var sessionDuration: Int = 0             // seconds, counts up while active
    @Published var waveformValues: [Float]              // count from ws_server.py waveform event
    @Published var pendingYellow: YellowConfirmRequest? = nil
    @Published var pendingRed: RedAuthRequest? = nil
    @Published var isSessionActive: Bool = false

    private var wsClient: WebSocketClient
    private var sessionTimer: AnyCancellable?
    private var agentProcess: Process?

    // startSession() → launches Python via Process(), starts WebSocket connection
    // stopSession()  → terminates Process, closes WebSocket, resets all state
    // respondToYellow(confirmed: Bool) → sends yellow_response via WebSocket
    // pollRedAuth(id: String) → polls GET /auth/status/{id} every 2s until resolved or timeout
}
```

**`startSession()` must:**
1. Launch `main.py` via `Process()` with env vars read from Keychain
2. Open WebSocket connection to `ws://localhost:8765`
3. Start session timer

**`stopSession()` must:**
1. Terminate the Process
2. Close WebSocket
3. Reset `status`, `actions`, `waveformValues`, `pendingYellow`, `pendingRed`, `sessionDuration`

---

### macOS Views

All views consume only `@ObservedObject var vm: AegisMacViewModel`. No local state that duplicates ViewModel state. Reference `Stitch/` for visual layout only.

#### `IdleView.swift`
- Shows when `vm.status == .idle && !vm.isSessionActive`
- Mic button calls `vm.startSession()`
- Breathing animation on mic button: scale 1.0→1.05, `repeatForever`, `autoreverses: true`, 2s
- Purple glow shadow on mic button

#### `ListeningView.swift`
- Shows when `vm.status == .listening`
- Waveform: render `vm.waveformValues` as vertical bars, animate with `.easeInOut(duration: 0.1)`
- Session timer: display `vm.sessionDuration` formatted as `M:SS`
- Stop button: calls `vm.stopSession()`
- Transitions to `ActivityStreamView` when first ActionCard arrives in `vm.actions`

#### `ActivityStreamView.swift`
- Shows when `vm.status == .executing && !vm.actions.isEmpty`
- Render `vm.actions` as scrollable cards, newest on top
- Each card: left border color from `action.tier.color`, action name, tool, duration, status icon
- Cards beyond position 5 fade to 60% opacity
- Max 20 cards (drop oldest beyond 20)
- Tap card → sheet showing full `action.reason` and arguments
- Stop button always visible, calls `vm.stopSession()`
- Spring animation on new card insertion

#### `YellowPauseView.swift`
- Overlay, shows when `vm.pendingYellow != nil`
- Dims everything beneath to 30% opacity
- Shows `vm.pendingYellow!.question` in an amber pulsing card
- "Proceed" → `vm.respondToYellow(confirmed: true)`
- "Skip" → `vm.respondToYellow(confirmed: false)`
- Amber glow pulse animation on the card

#### `RedAuthView.swift`
- Full-screen overlay, shows when `vm.pendingRed != nil`
- Blocks all interaction behind it
- Shows `vm.pendingRed!.action` and `vm.pendingRed!.reason`
- Countdown: 30 seconds from `vm.pendingRed!.requestedAt`, live countdown bar
- Polls `GET https://apiaegis.projectalpha.in/auth/status/{id}` every 2 seconds
- On approved: green flash animation → dismiss overlay → action continues
- On denied or timeout: red flash animation → dismiss overlay → action blocked
- "Check your iPhone" instruction text

---

## iOS App — `AegisApp_ios/`

### Data Source

The iOS app does NOT connect to the local WebSocket. It reads from:
- **Firestore** `audit_log` collection — real-time listener for the action mirror
- **FCM push notifications** — triggers RED auth request screen
- **GCP API** — for approve/deny and session stop

Read `backend/firestore.py` and `backend/main.py` to get exact Firestore collection names, document shapes, and API endpoint contracts before writing any iOS networking code.

---

### `FirestoreClient.swift` (iOS)

```swift
// Real-time listener on Firestore audit_log collection
// Read backend/firestore.py for exact collection name, field names, ordering
// Publishes [ActionCard] sorted by timestamp descending
// Publishes Bool for whether a session is currently active
// Publish RedAuthRequest when a pending auth document appears in Firestore
```

---

### `AegisIOSViewModel.swift`

```swift
@MainActor
final class AegisIOSViewModel: ObservableObject {
    @Published var actions: [ActionCard] = []           // live from Firestore
    @Published var isSessionActive: Bool = false         // live from Firestore
    @Published var pendingRedAuth: RedAuthRequest? = nil // from FCM + Firestore
    @Published var lastAuthResult: AuthResult? = nil     // approved/denied

    enum AuthResult { case approved, denied }

    private var firestoreClient: FirestoreClient

    // stopSession() → POST https://apiaegis.projectalpha.in/session/stop
    // approveRedAuth(id: String) → POST /auth/approve/{id} with approved: true + Face ID
    // denyRedAuth(id: String)   → POST /auth/approve/{id} with approved: false
}
```

---

### iOS Views

#### `MirrorView.swift`
- Root view
- If `vm.isSessionActive == false`: show "No active session" — real empty state from Firestore, not a fake placeholder
- If active: show `vm.actions` as scrollable list with tier-colored left borders
- STOP SESSION button: always visible at bottom, calls `vm.stopSession()`
- Updates in real time as Firestore listener fires

#### `RedAuthRequestView.swift`
- Presented when `vm.pendingRedAuth != nil` (from FCM notification or Firestore watch)
- Shows exact `pendingRedAuth.action` and `pendingRedAuth.reason` — no paraphrasing
- "Approve with Face ID" button:
  1. Calls `LAContext.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics)`
  2. On success → `vm.approveRedAuth(id:)`
  3. On failure → `vm.denyRedAuth(id:)`
- "Deny" button: calls `vm.denyRedAuth(id:)` directly
- Live countdown from `pendingRedAuth.expiresAt` — auto-deny when it hits zero
- Countdown bar updates every second

#### `PostAuthView.swift`
- Shows when `vm.lastAuthResult != nil`
- Green checkmark + "Approved" or red X + "Denied" — from actual `vm.lastAuthResult`
- Scale-in animation on appear
- Auto-dismisses after exactly 2 seconds → back to MirrorView
- Sets `vm.lastAuthResult = nil` on dismiss

---

## FCM Push Notifications (iOS)

Read `backend/fcm.py` for exact notification payload shape before implementing.

```swift
// AppDelegate or @UIApplicationDelegateAdaptor:
// 1. Request notification authorization on launch
// 2. Register FCM token with backend: POST https://apiaegis.projectalpha.in/device/register
//    Body: match exact shape from backend/main.py /device/register endpoint
// 3. On notification receipt with type "red_auth_request":
//    Extract request_id, action, reason from payload (match backend/fcm.py payload keys exactly)
//    Navigate to RedAuthRequestView
```

---

## Python Agent Launch (macOS only)

```swift
// In AegisMacViewModel.startSession():
func startSession() async throws {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")

    // Read main.py path from config — do not hardcode
    let repoPath = try KeychainHelper.read(key: "aegis_repo_path")
    process.arguments = ["\(repoPath)/main.py"]

    // Read from Keychain only — never hardcode
    process.environment = [
        "GOOGLE_API_KEY":    try KeychainHelper.read(key: "google_api_key"),
        "COMPOSIO_API_KEY":  try KeychainHelper.read(key: "composio_api_key"),
        "BACKEND_URL":       "https://apiaegis.projectalpha.in",
        "DEVICE_ID":         "harshit-macbook"
    ]

    try process.run()
    self.agentProcess = process
    self.isSessionActive = true
}
```

---

## API Endpoints Reference

Read `backend/main.py` for complete contract. Key endpoints:

| Method | URL | Used By |
|--------|-----|---------|
| `POST` | `/action` | macOS → backend after each action |
| `POST` | `/auth/request` | macOS → backend when RED tier fires |
| `GET`  | `/auth/status/{id}` | macOS polls every 2s |
| `POST` | `/auth/approve/{id}` | iOS → approve or deny |
| `GET`  | `/audit/stream` | SSE (dashboard only, not native apps) |
| `GET`  | `/audit/log` | paginated history if needed |
| `POST` | `/session/stop` | iOS kill switch |
| `POST` | `/device/register` | iOS FCM token registration |

---

## Animations — Must Feel Native

- New ActionCard insertion: `.spring(response: 0.4, dampingFraction: 0.7)`
- Waveform bars: `.easeInOut(duration: 0.1)` per frame
- Mic breathing: `repeatForever(autoreverses: true)` 2s duration
- Yellow card pulse: `repeatForever(autoreverses: true)` 1.2s, scale 1.0→1.02 + amber glow
- Red flash on auth result: `.easeOut(duration: 0.3)` color overlay
- Post-auth checkmark: scale 0→1 with `.spring(response: 0.5, dampingFraction: 0.6)`
- Post-auth shake (denied): keyframe horizontal offset animation

All animations must run at 60fps. No janky transitions.

---

## Build Order

Build and verify in this exact sequence. Do not skip ahead.

1. Read all backend files listed above
2. Create shared models (`ActionCard`, `AgentStatus`, `RedAuthRequest`, `YellowConfirmRequest`)
3. Build `WebSocketClient.swift` — verify it connects and parses real events from running Python agent
4. Build `AegisMacViewModel.swift` — verify all `@Published` vars update correctly from WebSocket
5. Build macOS views in order: `IdleView` → `ListeningView` → `ActivityStreamView` → `YellowPauseView` → `RedAuthView`
6. Build `FirestoreClient.swift` — verify real-time listener fires on Firestore writes
7. Build `AegisIOSViewModel.swift`
8. Build iOS views: `MirrorView` → `RedAuthRequestView` → `PostAuthView`
9. Wire FCM notifications end to end
10. Test full flow: voice command → classification → GREEN silent → YELLOW confirm → RED iOS auth

**At each step: the feature must work with real data before moving to the next step.**

---

## Final Checklist Before Handing Back

- [ ] Zero compiler warnings
- [ ] Zero uses of mock/dummy data anywhere
- [ ] WebSocket reconnects automatically on disconnect
- [ ] Session timer resets correctly between sessions
- [ ] Actions list clears on new session start
- [ ] Firestore listener detaches properly when iOS app backgrounds
- [ ] FCM token re-registered on every launch
- [ ] All API keys read from Keychain
- [ ] Countdown timers on both platforms auto-deny at 0
- [ ] PostAuthView always auto-dismisses after exactly 2 seconds
- [ ] Kill switch on iOS actually stops the macOS session via API
- [ ] Stitch UI files used only for visual reference — no logic copied from them