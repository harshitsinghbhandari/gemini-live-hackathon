# Aegis — Project Context
	⁠Last updated: March 5, 2026

---

## What Is Aegis?

Aegis is a voice-controlled, biometric-secured AI agent for Mac. It listens to your voice, sees your screen, classifies every action into a risk tier, and requires Touch ID for sensitive operations before executing anything via Composio.

*The core insight:* AI agents that control your computer are powerful but dangerous. Aegis is the first agent with a trust layer built in — every action is classified, logged, and gated by biometric auth when needed.

*Hackathon:* Gemini Live Agent Challenge (Google)
*Category:* UI Navigator (with strong Live Agent elements)
*Prize target:* Grand Prize ($25,000)
*Deadline:* ~10 days remaining

---

## The Three-Tier Security Model

| Tier | Color | Trigger | Auth | Examples |
|------|-------|---------|------|---------|
| Silent | 🟢 GREEN | Read-only actions | None | Fetch emails, check calendar |
| Confirm | 🟡 YELLOW | Reversible but sensitive | Verbal confirmation | Create draft, create calendar event |
| Biometric | 🔴 RED | Irreversible / financial | Touch ID / Face ID | Send email, delete files, payments |

Gemini acts as the *dynamic risk classifier* — it reads context intelligently. A file named "tax-return-2024" gets upgraded from GREEN to RED automatically.

---

## Full Architecture


USER SPEAKS (hotkey or menu bar click)
        ↓
Gemini Live API (voice input, real-time)
        ↓
Risk Classifier (Gemini Vision + prompt)
        ↓
┌─────────────────────────────────┐
│           AUTH GATE             │
│  🟢 → execute silently          │
│  🟡 → Gemini asks "proceed?"    │
│  🔴 → Touch ID required         │
└─────────────────────────────────┘
        ↓
Composio Tool Router
(finds right tool from natural language)
        ↓
Tool executes (Gmail, Calendar, etc.)
        ↓
Result → GCP Backend (FastAPI + Firestore)
        ↓
Dashboard updates in real time (SSE)
        ↓
Gemini speaks result back to user


---

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Voice | Gemini Live API (⁠ gemini-live-2.5-flash-native-audio ⁠) | Real-time voice input/output |
| Vision | Gemini Vision (⁠ gemini-2.5-flash ⁠) | Screen capture + risk classification |
| Actions | Composio Tool Router | Finds + executes correct tool from natural language |
| Biometric | macOS LocalAuthentication (pyobjc) | Touch ID / Face ID gate |
| Audio | PyAudio | Mic input + speaker output |
| Backend | FastAPI on GCP Cloud Run | Audit log, remote auth, SSE stream |
| Database | GCP Firestore | Real-time audit log storage |
| Dashboard | React + Vite on GCP Cloud Run | Live action feed for judges |
| Notifications | Firebase Cloud Messaging | iPhone PWA push notifications (planned) |

---

## Live URLs

| Service | URL |
|---------|-----|
| Dashboard | https://aegis.projectalpha.in |
| Backend API | https://apiaegis.projectalpha.in |
| Health check | https://apiaegis.projectalpha.in/health |

---

## GCP Resources

| Resource | Name |
|----------|------|
| Project | ⁠ guardian-agent-160706 ⁠ |
| Region | ⁠ us-central1 ⁠ |
| Cloud Run (backend) | ⁠ guardian-backend ⁠ |
| Cloud Run (dashboard) | ⁠ guardian-dashboard ⁠ |
| Artifact Registry | ⁠ guardian ⁠ |
| Firestore | default database |

	⁠Note: GCP resource names are fixed as "guardian-*" — cannot rename without breaking deployments.

---

## Project Structure


gemini-live-hackathon/
├── aegis/                    # Core agent package
│   ├── __init__.py
│   ├── config.py             # All env vars and constants
│   ├── context.py            # GuardianContext dataclass
│   ├── screen.py             # Screenshot capture
│   ├── classifier.py         # Gemini risk classification
│   ├── auth.py               # Touch ID gate
│   ├── executor.py           # Composio Tool Router + execution
│   ├── gate.py               # Orchestrates classifier + auth + executor
│   └── voice.py              # Gemini Live voice loop
├── backend/                  # GCP FastAPI backend
│   ├── main.py               # FastAPI app + all endpoints
│   ├── firestore.py          # Firestore client
│   ├── fcm.py                # Firebase Cloud Messaging
│   ├── models.py             # Pydantic models
│   ├── config.py             # Backend env vars
│   ├── Dockerfile
│   └── requirements.txt
├── dashboard/                # React dashboard
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── AgentStatus.jsx
│   │   │   ├── StatsBar.jsx
│   │   │   ├── AuditLog.jsx
│   │   │   ├── ActionDetail.jsx
│   │   │   └── TierBadge.jsx
│   │   ├── hooks/
│   │   │   ├── useAuditStream.js
│   │   │   └── useAuditLog.js
│   │   └── utils/formatters.js
│   ├── Dockerfile
│   └── nginx.conf
├── aegis_menubar.py          # Mac menu bar app (in progress)
├── main.py                   # CLI entry point (for testing)
├── deploy.sh                 # Single command GCP deployment
├── requirements.txt
├── .env
├── CONTEXT.md                # This file
├── CHANGES.md                # All changes Jules made
├── ISSUES_FOUND.md           # Bugs found during audit
└── README.md


---

## Environment Variables

⁠ env
# Gemini
GOOGLE_API_KEY=...

# Composio
COMPOSIO_API_KEY=...
COMPOSIO_USER_ID=harshitbhandari0318

# GCP
PROJECT_ID=guardian-agent-160706
BACKEND_URL=https://apiaegis.projectalpha.in
DASHBOARD_URL=https://aegis.projectalpha.in

# Device
DEVICE_ID=harshit-macbook
 ⁠

---

## Backend API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | ⁠ /health ⁠ | Health check |
| POST | ⁠ /action ⁠ | Mac agent posts completed action |
| POST | ⁠ /auth/request ⁠ | Mac requests remote auth (RED tier) |
| GET | ⁠ /auth/status/{id} ⁠ | Mac polls for approval |
| POST | ⁠ /auth/approve/{id} ⁠ | iPhone approves/denies |
| GET | ⁠ /audit/stream ⁠ | SSE stream for dashboard |
| GET | ⁠ /audit/log ⁠ | Paginated audit history |

---

## Composio Integrations

| Toolkit | Status | Key Tools |
|---------|--------|-----------|
| Gmail | ✅ Connected | FETCH_EMAILS, CREATE_DRAFT, REPLY |
| Google Calendar | ✅ Connected | GET_EVENTS, CREATE_EVENT |
| Slack | 🔲 Planned | SEND_MESSAGE, READ_CHANNEL |
| Google Drive | 🔲 Planned | SEARCH, UPLOAD, SHARE |
| Notion | 🔲 Planned | CREATE_PAGE, SEARCH |
| GitHub | 🔲 Planned | CREATE_ISSUE, CHECK_PRS |
| Spotify | 🔲 Planned | PLAY, SEARCH |

---

## Git Tags (Milestones)

| Tag | Description |
|-----|-------------|
| ⁠ v0.1.0-core ⁠ | Core agent working — voice, auth gate, Composio |
| ⁠ v0.2.0-gcp ⁠ | GCP backend deployed to Cloud Run |
| ⁠ v0.3.0-dashboard ⁠ | Dashboard deployed to Cloud Run |
| ⁠ v0.4.0-full-stack ⁠ | Full stack working end to end |
| ⁠ v0.5.0-all-tiers ⁠ | All three tiers GREEN/YELLOW/RED working |
| ⁠ v0.6.0-domain ⁠ | Custom domain mapped |
| ⁠ v0.7.0-domains-live ⁠ | Both domains live and healthy |
| ⁠ v0.8.0-aegis ⁠ | Rebranded from Guardian to Aegis |

---

## What's Working Right Now

•⁠  ⁠✅ Voice input via Gemini Live (continuous, interruptible)
•⁠  ⁠✅ Risk classification (GREEN/YELLOW/RED) with dynamic upgrading
•⁠  ⁠✅ GREEN — silent execution, no interruption
•⁠  ⁠✅ YELLOW — Gemini asks conversationally, listens for yes/no
•⁠  ⁠✅ RED — Touch ID fires natively on Mac
•⁠  ⁠✅ Composio Tool Router — finds correct tool from natural language
•⁠  ⁠✅ Gmail — fetch, draft, reply
•⁠  ⁠✅ Google Calendar — get events, create events
•⁠  ⁠✅ GCP Backend — FastAPI on Cloud Run
•⁠  ⁠✅ Firestore — real-time audit log
•⁠  ⁠✅ Dashboard — live at aegis.projectalpha.in
•⁠  ⁠✅ SSE stream — dashboard updates in real time
•⁠  ⁠✅ Audit trail — every action logged with full metadata
•⁠  ⁠✅ Custom domains — aegis.projectalpha.in + apiaegis.projectalpha.in
•⁠  ⁠✅ Structured logging — guardian.log + guardian_audit.jsonl

---

## What's In Progress

•⁠  ⁠🔄 Menu bar app (⁠ aegis_menubar.py ⁠) — Jules building now
  - Click or Cmd+Shift+A to start session
  - Icons: ◈ idle / ◉ listening / ◌ executing / ⊠ auth / ⊗ error
  - 60 second auto-timeout
  - "Open Dashboard" menu item

---

## What's Left to Build

### Must (required to submit)
•⁠  ⁠[ ] Menu bar app working and stable
•⁠  ⁠[ ] Tools expansion — Slack, Drive, GitHub, Notion
•⁠  ⁠[ ] iPhone PWA for remote RED auth (push notification → Face ID on iPhone)
•⁠  ⁠[ ] Wire Mac agent → posts to GCP backend after every action
•⁠  ⁠[ ] Architecture diagram (required for submission)
•⁠  ⁠[ ] Demo video — 4 minutes, Sarah scenario (30% of judging)
•⁠  ⁠[ ] Proof of GCP deployment recording

### Should (improves score)
•⁠  ⁠[ ] Rename Aegis everywhere in dashboard UI copy
•⁠  ⁠[ ] Blog post about building Aegis (bonus points)
•⁠  ⁠[ ] Infrastructure-as-code deploy script (bonus points)
•⁠  ⁠[ ] GDG profile signup (bonus points)

---

## The Demo Script (Sarah Scenario)

	⁠Sarah is a busy professional. She opens Aegis from her menu bar on a Monday morning.

 1.⁠ ⁠"Handle my morning"
 2.⁠ ⁠Agent checks emails → 🟢 GREEN, silent
 3.⁠ ⁠Agent checks today's calendar → 🟢 GREEN, silent  
 4.⁠ ⁠Agent creates a draft reply to her manager → 🟡 YELLOW, asks "shall I proceed?"
 5.⁠ ⁠Sarah says "yes"
 6.⁠ ⁠Agent sees an invoice to pay → 🔴 RED, Touch ID fires
 7.⁠ ⁠Sarah authenticates with fingerprint
 8.⁠ ⁠Payment draft created
 9.⁠ ⁠Dashboard at aegis.projectalpha.in shows every step live
10.⁠ ⁠Sarah says "done" — session ends

*That's the entire pitch in 90 seconds.*

---

## Judging Criteria Mapping

| Criteria | Weight | How Aegis Addresses It |
|----------|--------|----------------------|
| Innovation & Multimodal UX | 40% | Biometric-gated agentic control — never done before. Voice + vision + Touch ID seamlessly. |
| Technical Implementation | 30% | Gemini Live + ADK + Composio Tool Router + GCP Cloud Run + Firestore. Clean architecture. |
| Demo & Presentation | 30% | Sarah scenario shows all 3 tiers. Live dashboard. Custom domain. Architecture diagram. |

---

## The Winning Narrative

	⁠"AI agents are powerful. But power without trust is dangerous. Aegis is the first AI agent you can actually trust with your computer — because every action is classified, every sensitive operation requires your fingerprint, and everything is logged transparently. This isn't just an agent. It's trust infrastructure for the agentic era."