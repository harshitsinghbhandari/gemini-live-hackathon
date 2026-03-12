# Aegis — The Biometric AI Layer for Agents

**Aegis** is a trust-first AI agent that controls your Mac using the Gemini Live API and Composio. It bridges the gap between powerful agentic control and personal security by classifying every action into risk tiers (Green/Yellow/Red) and gating sensitive operations with biometric authentication (Touch ID on Mac or Face ID on iPhone).

---

## 🛡️ The Three-Tier Security Model

Every request to Aegis is analyzed against the current screen context and user intent before execution.

| Tier | Color | Risk Level | Authorization Mode | Examples |
| :--- | :--- | :--- | :--- | :--- |
| **Silent** | 🟢 GREEN | Low (Read-only) | Automatic | Fetch emails, list calendar events |
| **Confirm** | 🟡 YELLOW | Medium (Reversible) | Verbal Confirmation | Create email draft, add calendar event |
| **Biometric** | 🔴 RED | High (Irreversible) | Touch ID / Face ID | Send email, delete files, make payments |

---

## 🏗️ System Architecture

Aegis is a multi-component ecosystem designed for local control and remote monitoring:

1.  **Aegis Agent (Python)**: The "brain" running on your Mac. It communicates with Gemini Live via WebSockets, captures the screen, and executes tools.
2.  **Menubar App (Python/Rumps)**: A lightweight native Mac interface to start/stop sessions and monitor agent status.
3.  **GCP Backend (FastAPI)**: A central hub for logging actions, streaming live audits via SSE, and routing remote auth requests to mobile devices.
4.  **Mac Dashboard (React)**: A local web UI that connects to the agent via WebSockets for real-time visualization of the AI's thought process.
5.  **Mobile App (PWA React)**: A companion app that receives push notifications for RED actions, allowing you to approve high-risk tasks using your phone's biometrics.

### Data Flow
- **Voice Loop**: User Audio ↔ Gemini Live ↔ Aegis Agent ↔ PyAudio.
- **Action Gate**: Action String ↔ Gemini Classifier ↔ Auth Gate (Local/Remote) ↔ Composio.
- **Live Stream**: Agent ↔ Local WebSocket ↔ Mac Dashboard.
- **Audit Logging**: Agent ↔ FastAPI Backend ↔ Firestore ↔ SSE ↔ Remote Dashboards.

---

## 📂 Project Structure

```text
.
├── aegis/                # Core Voice Agent (GenAI + Composio)
│   ├── voice.py          # Gemini Live connection & loop
│   ├── gate.py           # Risk classification & auth routing
│   ├── auth.py           # Native macOS Touch ID (pyobjc)
│   ├── classifier.py     # Gemini risk assessment prompts
│   ├── screen.py         # Screenshot utility
│   ├── executor.py       # Composio Tool execution
│   └── ws_server.py      # Local WebSocket server for Mac Dashboard
├── backend/              # FastAPI Cloud Service
│   ├── main.py           # API endpoints & logic
│   ├── firestore.py      # Persistence layer
│   └── fcm.py            # Firebase Cloud Messaging for Push
├── mac-app/              # Native-feel dashboard (React + Vite)
├── mobile-app/           # PWA Approval app (React + Vite)
├── aegis_menubar.py      # Main entry point (Mac App)
├── .agent/               # Agent context & workflows
└── deploy.sh             # GCP Cloud Run deployment script
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Composio Account](https://composio.dev)
- Google Cloud Project with Gemini API access

### 1. Environment Setup
Create a `.env` in the root directory:
```env
GOOGLE_API_KEY=your_gemini_key
COMPOSIO_API_KEY=your_composio_key
COMPOSIO_USER_ID=your_id
PROJECT_ID=your_gcp_project_id
BACKEND_URL=https://your-backend-url.a.run.app
DASHBOARD_URL=http://localhost:3001
DEVICE_ID=your-device-name
```

### 2. Local Agent & Menubar
```bash
pip install -r requirements.txt
python aegis_menubar.py
```
*Note: Use `Cmd+Shift+A` or the menu icon to toggle the session.*

### 3. Mac Dashboard (Mac App)
```bash
cd mac-app
npm install
npm run dev -- --port 3001
```

### 4. Backend (Optional - Development)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 🛠️ Composio Integrations
Aegis currently supports:
- **Gmail**: Read, draft, and reply.
- **Google Calendar**: View and schedule events.
- **System Control**: Screen state awareness and local biometric integration.

---

## 🏆 Hackathon Context
- **Challenge**: Gemini Live Agent Challenge
- **Category**: UI Navigator / Personal Assistant
- **Winning Narrative**: "AI agents are powerful. But power without trust is dangerous. Aegis is the first agentic trust layer — every sensitive action requires your fingerprint, and every step is logged transparently."

---

## 📜 License
MIT © 2026 Harshit Singh Bhandari