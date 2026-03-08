# 1. Purpose of Aegis
Aegis is an AI agent that controls a macOS environment using the Gemini Live API and Composio tools while enforcing a strict security boundary. The core concept revolves around classifying every agentic action into three risk tiers: Silent (Green), Confirm (Yellow), and Biometric (Red), ensuring that sensitive operations cannot be executed without explicit user consent.

By analyzing the action context and screen state, Aegis prevents unauthorized or unintended operations. It gates high-risk actions behind native Touch ID on the Mac or Face ID on a companion mobile application, creating a secure bridge between autonomous AI capabilities and user verification.

# 2. Purpose of Helper Server (aegis/helper_server.py)
The Helper Server is a local FastAPI service running on port 8766 that manages the lifecycle of the main Python Aegis agent. It exposes specific HTTP endpoints (`/health`, `/start`, `/stop`, and `/status`) that allow the local frontend applications to securely spawn and terminate the `main.py` agent process without requiring the user to interact with a terminal environment.

This server exists to bridge the gap between browser-based web applications and native operating system process management. Without the Helper Server, the Mac App would lose all ability to start or stop the agent, severing the user's primary means of controlling the underlying background process.

# 3. Purpose of Dashboard (dashboard/)
The Dashboard is a remote monitoring web application built with React, served locally on port 3000 and accessible in production at `https://aegis.projectalpha.in`. It is designed for users or administrators who need to review the agent's historical and real-time activity securely from any remote browser.

It retrieves its data by connecting to the main backend server via HTTP endpoints and Server-Sent Events utilizing the `useAuditLog` and `useAuditStream` hooks. The interface displays a live audit log, agent connection status, detailed action insights, and numerical statistics categorizing actions into Green, Yellow, Red, or Blocked tiers.

# 4. Purpose of Mac App (mac-app/)
The Mac App is a local React application served via Vite on port 3001 that acts as the primary native-feeling interface for controlling the Aegis agent directly on the host machine. It connects to the agent's local WebSocket server (`ws://localhost:8765`) to receive live state updates and audio waveform data, and it communicates via HTTP with the Helper Server (`http://localhost:8766`) to start or stop the agent process.

Its user interface consists of distinct structural pages including `IdlePage`, `ListeningPage`, `ActivityPage`, and overlay pages for `YellowPausePage` and `RedAuthPage`. These screens allow the user to visually track the AI's current operational state, review pending medium-risk actions, and initiate local biometric authorization without leaving the application.

# 5. Purpose of Mobile App (mobile-app/)
The Mobile App is a companion Progressive Web App built with React, running locally on port 3002 and available remotely at `https://aegismobile.projectalpha.in`. It serves as an out-of-band biometric authentication device, allowing users to remotely authorize or deny high-risk (Red) actions initiated by the Mac agent using their mobile phone's Face ID or Touch ID capabilities.

It functions by polling the remote backend API (`https://apiaegis.projectalpha.in`) using the `usePendingAuth` hook to check for pending authorization requests targeting its specific device ID. The application UI cycles through a state machine, displaying a `MirrorPage` while waiting, transitioning to a `RedAuthPage` when an action requires approval, and showing a `PostAuthPage` once the authorization result is submitted back to the server.
