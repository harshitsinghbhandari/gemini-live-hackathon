# ◈ Aegis
### Trust infrastructure for the agentic era.

[Live Demo](https://aegis.projectalpha.in) · 
[Mac App](https://aegismac.projectalpha.in) · 
[Dashboard](https://aegisdashboard.projectalpha.in) ·
[Setup](https://aegis.projectalpha.in/setup)

Built for the Gemini Live Agent Challenge

## What is Aegis

Aegis is a voice-controlled, biometric-secured AI agent for macOS that controls the screen using the Gemini Live API with native ComputerUse. It acts as a "Trusted Pilot" for your computer, enforcing a strict security boundary by classifying every agentic action into three risk tiers: Silent (Green), Confirm (Yellow), and Biometric (Red).

By combining real-time vision (continuous delta-based screenshot streaming) with a robust state machine (LISTENING/THINKING/EXECUTING/BUSY), Aegis executes multi-step tasks autonomously while ensuring sensitive operations—like deleting files or sending emails—cannot be executed without explicit user consent via native Touch ID on the Mac or Face ID on a companion mobile app.

## The Three-Tier Security Model

| Tier | Actions | Auth Required |
| --- | --- | --- |
| 🟢 GREEN | Read-only / Navigation | None |
| 🟡 YELLOW | UI Interaction / Creation | Voice confirmation |
| 🔴 RED | Irreversible / Sensitive | Touch ID / Face ID |

## Architecture

Aegis utilizes a high-speed duplex stream of audio and video with the Gemini Live API, managed by a dedicated state machine.

```mermaid
graph TD
    %% Styling
    classDef default fill:#111,stroke:#333,stroke-width:1px,color:#fff;
    classDef userbox fill:#1e1e2e,stroke:#7c3aed,stroke-width:2px,color:#fff;
    classDef local fill:#0f172a,stroke:#3b82f6,stroke-width:1px,color:#fff;
    classDef cloud fill:#2d1b69,stroke:#8b5cf6,stroke-width:1px,color:#fff;
    classDef green fill:#064e3b,stroke:#16a34a,stroke-width:2px,color:#fff;
    classDef yellow fill:#78350f,stroke:#d97706,stroke-width:2px,color:#fff;
    classDef red fill:#7f1d1d,stroke:#dc2626,stroke-width:2px,color:#fff;
    classDef gemini fill:#4c1d95,stroke:#7c3aed,stroke-width:2px,color:#fff;

    User["👤 USER"]:::userbox
    MacPWA["💻 Mac PWA<br/>(Local UI)"]:::local
    Helper["⚙️ Helper Server<br/>(localhost:8766)"]:::local

    User -- "Speaks / Interacts" --> MacPWA
    MacPWA -- "Start/Stop" --> Helper

    subgraph "Local Mac Agent"
        WsServer["📡 WebSocket Server<br/>(ws://localhost:8765)"]:::local
        Voice["🎙️ voice.py<br/>(Audio & Video I/O)"]:::gemini
        Gemini{"✨ Gemini Live API"}:::gemini
        Classifier["🧠 classifier.py<br/>(Risk Analysis)"]:::local
        Gate["🛡️ gate.py<br/>(Auth Router)"]:::local
        
        State["🔄 State Machine<br/>(LISTENING/THINKING/EXECUTING/BUSY)"]:::local

        TierG["🟢 GREEN<br/>(Silent)"]:::green
        TierY["🟡 YELLOW<br/>(Voice Confirm)"]:::yellow
        TierR["🔴 RED<br/>(Biometric Auth)"]:::red
        
        Executor["⚡ screen_executor.py<br/>(Native ComputerUse)"]:::local
        Screen[/"🖥️ macOS Screen Control<br/>pyautogui, mss, clipboard"/]:::local

        MacPWA -. "Live State / Waveforms" .-> WsServer
        WsServer -.-> Voice
        Voice <--> Gemini
        Voice --> Classifier
        Classifier --> Gate
        Gate --> State
        State --> TierG
        State --> TierY
        State --> TierR
        TierG --> Executor
        TierY -- "Confirmed by Voice" --> Executor
        TierR -- "Approved by Mobile/TouchID" --> Executor
        Executor --> Screen
    end

    subgraph "GCP Backend (Cloud Run)"
        Backend["☁️ FastAPI Server"]:::cloud
        DB[("🗄️ Firestore<br/>users/{user_id}/*")]:::cloud
        
        Gate -- "POST /action<br/>POST /auth/request" --> Backend
        Backend --> DB
    end
    
    subgraph "User Devices"
        Dashboard["📊 Dashboard<br/>(Web Hub)"]:::userbox
        Mobile["📱 Mobile PWA<br/>(Companion App)"]:::userbox
        
        Backend -- "GET /audit/stream<br/>(SSE)" --> Dashboard
        Backend -- "GET /auth/pending" --> Mobile
        Mobile -- "POST /webauthn/auth/verify" --> Backend
    end
```

## Tech Stack

| Component | Technology |
| --- | --- |
| Voice & Vision | Gemini Live API |
| AI Model | Gemini 2.5 Flash |
| Desktop Control | Native ComputerUse (pyautogui + mss) |
| Biometric (Mac) | macOS LocalAuthentication (pyobjc) |
| Biometric (iPhone) | WebAuthn / Face ID |
| Backend | FastAPI on GCP Cloud Run |
| Database | GCP Firestore |
| Mac App | React PWA |
| Mobile App | React PWA |
| Dashboard | React + SSE |

## Demo Scenario

Aegis can execute complex, multi-step tasks autonomously. For example:
> "Open the Gemini Live Agent Challenge page and paste the rules into a new Google Doc."

Aegis will:
1.  Open Chrome and navigate to the challenge page.
2.  Extract the rules from the page.
3.  Open a new Google Doc.
4.  Paste the rules and name the document.
5.  All while gating the final "Create" or "Save" actions behind your preferred security tier.

## Quick Start (5 minutes)

1. Visit [aegis.projectalpha.in/setup](https://aegis.projectalpha.in/setup)
2. Enter your API keys and set your AEGIS_PIN.
3. Run the install command.
4. Start the local helper server: `python3 -m aegis.helper_server`
5. Open [aegismac.projectalpha.in](https://aegismac.projectalpha.in) and start talking.

## Project Structure

```text
gemini-live-hackathon/
├── aegis/                 # Python agent core handling Gemini Live, Vision, and native Screen Control
│   ├── screen/            # Low-level drivers for cursor, typing, and capture
│   ├── classifier.py      # Risk tier analysis
│   ├── gate.py            # Security gateway and auth routing
│   ├── voice.py           # Real-time multimodal orchestration
│   └── screen_executor.py # Native ComputerUse execution
├── backend/               # FastAPI backend for audit logging, auth requests, and WebAuthn
├── dashboard/             # Remote React web dashboard for real-time monitoring
├── guides/                # Documentation for architecture and migration
├── mac-app/               # Local React UI for macOS (Voice visualizer & status)
├── mobile-app/            # Companion PWA for remote biometric verification
├── aegis_menubar.py       # macOS native menu bar utility
├── architecture.mermaid   # System architecture diagram
├── install.sh             # Automated installation script
└── main.py                # Agent entry point
```

## Live Deployments

| Service | URL |
| --- | --- |
| Landing | [https://aegis.projectalpha.in](https://aegis.projectalpha.in) |
| Dashboard | [https://aegisdashboard.projectalpha.in](https://aegisdashboard.projectalpha.in) |
| Mac App | [https://aegismac.projectalpha.in](https://aegismac.projectalpha.in) |
| Mobile App | [https://aegismobile.projectalpha.in](https://aegismobile.projectalpha.in) |
| API | [https://apiaegis.projectalpha.in](https://apiaegis.projectalpha.in) |

## Built By

Harshit Singh Bhandari

Built for the Gemini Live Agent Challenge — March 2026
