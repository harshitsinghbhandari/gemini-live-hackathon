---
title: "Aegis"
description: "A Gemini Live desktop agent with a graduated trust gate, native macOS screen control, and out-of-band biometric authorization."
status: "case-study-draft"
project: "Gemini Live Agent Challenge"
stack:
  - Python
  - Gemini Live API
  - FastAPI
  - Firestore
  - React PWA
  - WebAuthn
  - macOS Accessibility
---

# Aegis

Aegis is a macOS agent that can listen, see the screen, call tools, and operate the desktop — but every action passes through a trust boundary before it touches the machine.

The core design question was not "can an AI agent click things?" It was: **what has to sit between a real-time multimodal model and a real user account before desktop automation becomes acceptable?**

Aegis answers that with a three-tier execution model:

| Tier | Action class | Authorization path |
| --- | --- | --- |
| Green | Read-only, navigation, state inspection | Silent execution |
| Yellow | Reversible mutation, UI interaction, drafting | Passive voice confirmation |
| Red | Irreversible, sensitive, financial, destructive, or externally visible actions | WebAuthn Face ID / macOS Touch ID |

The system was built for the Gemini Live Agent Challenge, but the interesting part is the boundary architecture: a local desktop agent for low-latency perception and execution, a cloud broker for out-of-band authorization, and a persistent audit plane for observability.

## The System

Aegis runs as a local Python agent on macOS. The agent maintains a duplex Gemini Live session, streams microphone audio and visual context, receives model tool calls, classifies each requested action, and only then dispatches it to native screen-control tools.

The user-facing surface is split into three small applications:

- **Mac PWA**: local control surface for session state, waveform, live action cards, and red-action authorization status.
- **Mobile PWA**: companion authorization device for red-tier actions using WebAuthn / Face ID.
- **Dashboard PWA**: audit stream for historical and real-time actions.

The local agent is intentionally not a browser automation wrapper. It uses screenshots, OCR, active-window crops, cursor tools, keyboard tools, and `pyautogui` to operate the visible desktop. That means the same execution path can target any application the user can see, but it also means the system has to solve grounding, latency, and authorization at the screen layer rather than relying on typed API contracts.

## The Architecture

Aegis is a hybrid system: local for perception and actuation, cloud for authentication coordination and auditability.

```text
User voice + macOS screen
        ↓
Local Python agent
  - Gemini Live duplex session
  - state machine: LISTENING / THINKING / EXECUTING / BUSY
  - delta-based active-window screenshot stream
  - RapidOCR background cache
        ↓
Gemini tool call
        ↓
Aegis gate
  - secondary Gemini classifier
  - Green / Yellow / Red decision
  - audit envelope construction
        ↓
Execution path
  Green  → native screen tool executes immediately
  Yellow → verbal confirmation listener → native screen tool
  Red    → Cloud Run auth request → Mobile WebAuthn / local Touch ID → native screen tool
        ↓
Post-action screenshot + tool response returned to Gemini Live
        ↓
Audit log streamed to dashboard via Firestore + SSE
```

### Local agent

The agent entry point initializes an `AegisContext` and starts `AegisVoiceAgent`. That context is the coordination point for session state, Gemini session handles, resumability, and OCR cache.

The Gemini Live connection is configured for audio responses, native activity detection, thought streaming, sliding-window compression, and function declarations for the screen-control tools. The agent runs separate async loops for:

- sending microphone audio;
- receiving Gemini audio, thoughts, tool calls, and turn-complete events;
- sending visual frames;
- forwarding live status to the Mac PWA over `ws://localhost:8765`.

A lightweight helper server on `localhost:8766` gives the PWA a way to start, stop, and inspect the Python process without requiring the user to touch the terminal.

### Perception pipeline

The visual stream is foveated. Instead of sending the entire desktop on every interval, the agent attempts to capture the active window with padding, records the crop origin, and only sends a new JPEG frame when its hash changes or the model enters a thinking transition.

That crop-origin bookkeeping matters. Gemini works over normalized visual coordinates; the executor has to map those back into actual macOS coordinates. When a crop is active, `get_noisy_center` maps the model's `[ymin, xmin, ymax, xmax]` box into the crop's physical screen region. When no crop is active, it maps against the full `pyautogui` screen size.

A parallel OCR loop keeps a local cache of text elements. It tiles the screen, only re-runs OCR on changed tiles, deduplicates boxes by IoU, and groups results into regions such as top bar, sidebars, and main content. Higher-level tools can then click by `label_id` or fuzzy text match instead of guessing coordinates. This is the practical difference between "the model thinks the button is around here" and "the system has a concrete text box with a current bounding region."

### Trust gate

The gate is the central invariant: **Gemini can propose an action; it cannot directly execute one.**

When Gemini emits a function call, the receive loop immediately moves the session into `EXECUTING`, purges stale media from the outbound queue, and calls `gate_action` with the tool name and arguments. The gate then asks a separate Gemini classifier to evaluate intent and consequence, not just the tool.

This separation is important. `keyboard_type` can be green if it is a search query, yellow if it drafts a message, or red if it enters a secret. `cursor_click` can be navigation, submission, or deletion depending on the visible context and intended outcome. The classifier returns a tier, reason, speech string, and tool metadata; parsing failures and unexpected classifier errors fail closed to Red.

The gate produces one audit envelope for every action attempt: timestamp, tier, tool, arguments, confirmation status, authentication status, block status, result, duration, and device.

### Execution tools

The execution layer is a registry of native screen tools:

- `screen_capture` and `screen_read` for visual state;
- `screen_crop` for high-resolution regions of interest;
- `get_screen_elements`, `get_annotated_elements`, and `click_by_word` for OCR-grounded targeting;
- `cursor_move`, `cursor_click`, `cursor_double_click`, `cursor_right_click`, `cursor_scroll`, and `cursor_drag` for pointer control;
- `keyboard_type`, `keyboard_press`, `keyboard_hotkey`, and `keyboard_type_sensitive` for text and key input.

Blocking calls such as screenshot capture and `pyautogui` actions are pushed into threads so they do not stall the async Gemini session. Cursor clicks also capture a small region before and after the click and compare hashes, giving the system a cheap signal for whether the UI changed.

### Cloud authorization and audit plane

The backend is FastAPI on Cloud Run with Firestore as the data plane. It handles:

- action logging via `POST /action`;
- pending Red requests via `POST /auth/request`, `GET /auth/status/{request_id}`, and `GET /auth/pending`;
- dashboard streaming via `GET /audit/stream` using Server-Sent Events;
- WebAuthn registration and assertion verification;
- session active/stop state for remote control.

For Red actions, the local agent creates an auth request and waits up to 30 seconds. The mobile PWA polls for pending requests, presents the action and reason, asks the user to approve with Face ID through WebAuthn, and sends the signed assertion back to the backend. The backend verifies the challenge against the stored credential public key and updates the Firestore request status. The local agent resumes only if the request becomes approved; otherwise it blocks or falls back to local Touch ID.

## The Implementation

The hardest part of Aegis was not wiring a model to a mouse. It was keeping a real-time Live API session, native desktop automation, and an authorization protocol from stepping on each other.

### 1. Preventing Live API policy violations during tool execution

A live multimodal session is sensitive to turn state. If the user keeps speaking or the visual loop keeps sending frames while the model is issuing tool calls, the session can hit policy errors. Aegis handles this with a hard state gate:

- media is only sent while the context is `LISTENING`;
- tool-call detection immediately switches to `EXECUTING`;
- queued audio/video packets are purged when execution starts;
- tool responses are sent as `LiveClientToolResponse`;
- post-action screenshots are sent back through realtime video input after the tool response.

This turns the Live session into an explicit state machine rather than a loose collection of async tasks.

### 2. Closing the perception-action loop

The model is only useful if its visual understanding survives the jump into OS coordinates. Aegis uses three layers to make that safer:

1. **Foveated capture**: active-window screenshots reduce irrelevant pixels and token use.
2. **Crop-aware coordinate mapping**: stored crop origins let the executor translate normalized model coordinates into screen coordinates.
3. **OCR-grounded targeting**: `click_by_word` and `label_id` clicks let the agent target named UI elements from a fresh OCR cache.

The result is a loop where every action can be followed by a fresh screenshot and function response, letting Gemini continue from the actual post-action state instead of an assumed one.

### 3. Separating capability from authority

Aegis does not trust the primary Live model to decide its own permissions. Tool calls are intercepted and classified through a second model call with a narrower prompt and JSON contract. That classifier evaluates irreversibility, sensitivity, external visibility, and state mutation.

The engineering trade-off is latency. The extra classifier call adds delay before execution. The benefit is a clean security seam: the model that plans the action is not the final authority on whether the action can run.

### 4. Making Red actions out-of-band

Red actions are not confirmed in the same desktop context where the agent is operating. The local agent sends an authorization request to the backend; the phone becomes the approval device.

The WebAuthn path avoids treating "tap approve" as enough. The mobile PWA asks the platform authenticator to sign a challenge; the backend verifies the assertion against the public key stored during registration, updates the request status, and only then can the local agent continue.

This is the critical safety property: even if the desktop agent is wrong, a destructive action still has to cross a second device and a cryptographic verification step.

### 5. Keeping an audit trail without blocking the agent

Every gated action is logged locally and posted to the backend. The dashboard consumes the Firestore-backed audit stream over SSE, so the observability path is separate from the local execution loop. If the backend is temporarily unavailable, local execution can continue for non-Red actions while backend posting degrades gracefully.

## Trade-offs

**PWA instead of native mobile app.** WebAuthn in mobile Safari gives access to device biometrics without App Store distribution, but push and background behavior are weaker than a native iOS app.

**Cloud model for visual reasoning.** Gemini Live gives strong multimodal understanding, but screenshot streaming has latency and token cost. The repo offsets this with active-window crops, hash-based frame suppression, and local OCR, but a production version would move more perception onto the device.

**Screen automation instead of API automation.** Native screen control works across arbitrary visible apps and matches what the user sees. It also inherits the fragility of visual grounding, window focus, app animations, and OS permissions.

**Secondary classifier.** The extra model call costs time, but it creates a narrow authorization boundary and a fail-closed path when parsing fails.

## Engineering Notes From the Repository

- The final architecture pivots away from browser/DOM automation toward screen-only ComputerUse. The changelog records this shift in the `v2.7.0-screen-agent` and `v3.0.0-navigation-stable` entries.
- The local agent uses `mss` for screenshots, `pyautogui` for native input, RapidOCR for local text extraction, and the Gemini SDK for Live sessions and classifier calls.
- The cloud backend stores per-user subcollections for audit logs, auth requests, device tokens, session state, and WebAuthn credentials.
- The code includes an intended visual-context handoff for Red requests: the agent captures a downscaled screenshot for mobile review, and the mobile RedAuth page renders `request.visual_context` when present. The backend model should persist that field explicitly to make this contract complete.
- The repository documents known production limits: macOS permissions, WebAuthn/PWA constraints, OAuth restrictions for sensitive Google scopes, and vision-token latency.

## Why This Matters

Most desktop-agent demos optimize for autonomy. Aegis optimizes for the boundary around autonomy.

The system assumes that an AI agent with a mouse is dangerous by default. It then builds the minimum infrastructure needed to make that danger governable: stateful Live orchestration, visual grounding, action classification, biometric escalation, audit logs, and explicit failure modes.

That is the architectural point of the project. Not a chatbot with a screen. A trust gate for a model that can act.

## Evidence Pointers

- Local Gemini Live orchestration: `packages/aegis/interfaces/voice.py`
- Session state model: `packages/aegis/runtime/context.py`
- Gate and Red auth flow: `packages/aegis/agent/gate.py`
- Risk classifier: `packages/aegis/agent/classifier.py`
- Native screen executor: `packages/aegis/runtime/screen_executor.py`
- Tool registry and screen tools: `packages/aegis/tools/*`
- Screenshot and active-window capture: `packages/aegis/perception/screen/capture.py`
- OCR cache: `packages/aegis/perception/screen/ocr.py`
- Local Touch ID: `packages/aegis/auth.py`
- Cloud backend: `services/backend/run_backend.py`, `services/backend/firestore.py`, `services/backend/models.py`
- Mobile WebAuthn client: `apps/mobile-app/src/components/FaceIDButton.jsx`
- Mac PWA websocket client: `apps/mac-app/src/hooks/useWebSocket.js`
- Architecture docs: `ARCHITECTURE.md`, `docs/security-model.md`, `docs/webauthn-flow.md`, `packages/aegis/flow.md`
