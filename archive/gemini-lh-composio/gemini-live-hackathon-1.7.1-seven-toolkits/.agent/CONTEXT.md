# Aegis - Project Context

This file contains comprehensive context about the Aegis repository to help any AI agent understand the architecture, core modules, and how everything interacts.

## 1. Project Overview & Architecture

**Aegis** (formerly Guardian) is an AI agent that controls a Mac computer using the Gemini Live API and Composio. It uses a multi-modal approach (Voice + Screen) to interpret user intent, classifies the security risk of actions, and executes them (often via Composio). High-risk actions (categorized as "RED") trigger a native TouchID/FaceID prompt or remote push notification approval before proceeding.

**Key Technical Stack**:
- **Python (Agent & Backend)**: Main application language for the voice agent and FastAPI backend.
- **Gemini Live API**: Handles real-time audio I/O and visual context (screenshots) and calls tools.
- **Composio**: Platform used to execute actual API actions (e.g., fetching emails, drafting emails).
- **FastAPI / Firebase (Backend)**: Handles auth requests, action logging, and live audit streams via SSE.
- **React + Vite (Frontends)**: Used for both a macOS menubar dashboard (`mac-app`) and a mobile PWA companion app (`mobile-app`).

## 2. Directory Structure

- `aegis_menubar.py`: The main entrypoint for the Mac menu bar application using `rumps`. Manages the background voice session and status overlay.
- `aegis/`: Core functional capabilities of the voice agent.
  - `voice.py`: Connects to Gemini's Live API, streams audio/screen, and handles tool execution routing.
  - `gate.py`: Classifies an action's risk. If RED, requests auth. If GREEN, executes directly.
  - `auth.py`: Wrapper around macOS LocalAuthentication to ask for Touch ID natively.
  - `classifier.py`: The raw prompt logic to ask Gemini to classify an action as RED/YELLOW/GREEN.
  - `screen.py`: Takes screenshots using PIL's `ImageGrab` and resizes them for Gemini.
  - `executor.py`: Wrapper for Composio's Python SDK to run tools or connect an app.
  - `ws_server.py`: Local WebSocket server to broadcast events to the local mac-app frontend.
- `backend/`: FastAPI backend service (`main.py`).
  - Manages Firestore (`firestore.py`) for logging, auth requests, and session status.
  - Handles push notifications via Firebase Cloud Messaging (`fcm.py`).
  - Connects to frontends to serve pending auth requests and audit streams.
- `mac-app/`: React + Vite web app serving as the Mac UI dashboard. Connects to local websockets and cloud backend.
- `mobile-app/`: React + Vite PWA serving as the mobile companion app. Handles FaceID/TouchID remote approvals for RED actions.
- `.agent/`: Stores agent-specific context files (like this one) and workflows.

---

## 3. Core Flow Reference

### Voice Agent Orchestration (`aegis/voice.py` & `aegis_menubar.py`)
`aegis_menubar.py` provides a native Mac menu bar icon. When started, it spins up an async loop running `run_aegis()` from `aegis/voice.py`.
The voice script initializes the `genai.Client`, connects to gemini's live api (`live.connect`), sets up system instructions, and exposes one main tool to Gemini: `execute_action(action: str)`.

### Security Routing (`aegis/gate.py`)
1. Receives an action string from the Voice Agent.
2. Captures a screenshot context.
3. Sends both to Gemini via `classify_action()` to determine tier.
4. Rules:
   - RED: Prompt for authorization. Depending on context, it can use the native Touch ID (`auth.py`) or forward an AuthRequest to the `backend` for the user to approve on their mobile device. 
   - YELLOW: Requires verbal/conversational confirmation.
   - GREEN: Executed silently.
5. If approved, runs the suggested Composio `tool` using the suggested `arguments` via `executor.py`.

### Remote Authentication Pipeline
When a RED action triggers remote auth:
1. `gate.py` creates a pending auth request via the FastAPI `backend`.
2. `backend` sends an FCM push notification to the registered `mobile-app`.
3. The user opens the `mobile-app`, authenticates using local device biometrics (FaceID/TouchID), and approves/denies.
4. The `backend` updates the auth status in Firestore.
5. `gate.py` polls or waits for the status to change and proceeds accordingly.

---

## 4. How to Extend
- **Adding new capabilities**: Define a new Composio tool or a local Python script function. Update the prompt in `aegis/classifier.py` and `aegis/gate.py` to make the classifier aware of the new tools and acceptable tool names.
- **Frontend changes**: Update the React code in `mac-app/` or `mobile-app/`. Both run via Vite (`npm run dev`).
- **Backend changes**: The FastAPI backend is typically run via uvicorn (`backend/main.py`). Use the `requirements.txt` in the `backend/` directory.
