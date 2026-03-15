# Aegis Architecture and System Design

## Philosophy and Core Design Decisions
Aegis was designed from the ground up to be a **local-first, cloud-secured** AI agent. It needs the low-latency responsiveness of a local application to monitor the screen continuously, but it requires the robust security of a cloud-based out-of-band authentication system to enforce its Three-Tier Security Model.

### Why Local-First?
An agent capable of "Native ComputerUse" (moving the mouse, taking screenshots, clicking buttons) must reside on the host machine. Streaming continuous desktop frames to a generic web server is not only a privacy nightmare but also introduces unacceptable latency.
Aegis runs a local Python agent (`cmd/agent/run_agent_main.py`) that captures the screen and audio locally. It manages its own state machine (`LISTENING/THINKING/EXECUTING/BUSY`) and handles execution locally using tools like `pyautogui` and `mss`.

### Why Native Screen Control?
Aegis interacts with the host OS and applications directly utilizing `screen_executor.py` and the Gemini Live API with high-resolution screenshot crops (`cursor_crop`, `get_annotated_elements`). This allows Aegis to navigate any app that is visible on the screen, just like a human, without needing brittle third-party integrations or OAuth tokens. It's a true "Trusted Pilot."

## System Components

### 1. Local Mac Agent (`packages/aegis/`)
This is the heart of Aegis, running entirely on the user's macOS device.

*   **`cmd/agent/run_agent_main.py`**: The main entry point for the agent. Handles real-time duplex streaming to the Gemini Live API, screen capture, and audio I/O.
*   **`agent/classifier.py`**: The "brain" of the trust boundary. It uses a secondary LLM call (Gemini 2.5 Flash) to parse an intent and classify it as GREEN, YELLOW, or RED.
*   **`agent/gate.py`**: The Auth Router. Enforces the security tier rules and manages authentication handshakes.
*   **`runtime/screen_executor.py`**: The native execution engine. Maps commands like `cursor_click` or `keyboard_type` to actual OS-level commands.
*   **`interfaces/helper_server.py`**: The Control Bridge (port 8766). A FastAPI server that allows the Mac PWA to start/stop the agent and perform maintenance tasks.

### 2. Local Communication: WebSockets & HTTP
Aegis uses two local ports for communication with the Mac PWA:
*   **Port 8765 (WebSocket)**: The agent (`run_agent_main.py`) streams live state, waveforms, and action logs directly to the PWA.
*   **Port 8766 (HTTP)**: The helper server (`helper_server.py`) provides an API for the PWA to control the agent's lifecycle (Start/Stop/Status).

### 3. The Frontends (React PWAs)
Aegis uses Progressive Web Apps (PWAs) instead of native applications.
*   **Mac PWA**: The local user interface showing real-time agent state, waveforms, and live action logs. It sends Start/Stop signals to the local helper server.
*   **Dashboard PWA**: The central hub for the user to view historical audit logs via Server-Sent Events (SSE) from the backend.
*   **Mobile PWA**: The companion app used for out-of-band biometric authentication. It registers a Face ID credential using the WebAuthn standard and polls the backend for pending "RED" action requests.

### 4. Cloud Run and Firestore Backend
The GCP Backend (`services/backend/run_backend.py`) is built with FastAPI and deployed on Google Cloud Run.

*   **Why Cloud Run?**: Serverless architecture allows the backend to scale to zero when not in use, keeping costs low while providing instantaneous spin-up times for authentication handshakes.
*   **Why Firestore?**: Firestore's real-time capabilities (`on_snapshot`) and NoSQL structure are perfect for Aegis. It handles active session status, audit logging, WebAuthn credentials, and most crucially, real-time polling for "auth_requests" (the RED tier biometric challenges).

## Tradeoffs Made
1.  **Latency vs. Security**: The secondary LLM call in `classifier.py` adds ~500-1000ms of latency before executing any action. This is a deliberate tradeoff: sacrificing absolute speed for absolute safety.
2.  **PWA vs. Native Mobile App**: A native iOS app could receive silent push notifications (APNs) faster. However, a PWA using WebAuthn allows for immediate cross-platform deployment without App Store review hurdles, while still securely utilizing the device's secure enclave (Face ID).
3.  **Local Vision vs. Cloud Vision Processing**: Sending screenshots continuously to Gemini consumes massive bandwidth and tokens. To mitigate this, Aegis uses local `mss` captures and `pyautogui` for execution, but relies on the cloud LLM to interpret the frames. Local OCR is also used (`aegis.perception.screen.ocr`) to supplement the cloud vision model, creating a hybrid approach that balances cloud intelligence with local precision.