# Aegis Changelog

This document summarizes the major version history of Aegis during the hackathon, based on the repository's git tags.

### [v3.2.0-screen-only-no-browser] - Final Cleanup
*   **Refactor:** Completely removed Playwright, DOM extraction, and all sub-agents that relied on browser-specific tools.
*   **Cleanup:** Removed the setup page and all its references from the landing page.
*   **Feature:** Integrated direct GitHub repository link for easier access to source code.

### [v3.0.0-navigation-stable] - Latest Stable Release
*   **Feature:** Reliable navigation via OCR + `label_id` clicking. The system successfully stabilizes the Native ComputerUse capabilities using purely visual analysis.

### [v2.8.0-refactor-monorepo] - Monorepo Structure
*   **Refactor:** The repository was refactored into a scalable monorepo structure utilizing absolute imports and centralized configs (`apps/`, `services/`, `packages/`, `configs/`, `cmd/`, `docs/`, `scripts/`, `env/`). Final sanity checks and frontend build confirmations were added.

### [v2.7.0-screen-agent] - The Pivot to Native ComputerUse
*   **Feature:** Complete pivot to a screen-only architecture. Composio toolkits were removed in favor of native, continuous visual monitoring and UI interaction.
*   **Feature:** Multi-step navigation and complex task execution working purely through visual means.

### [v2.6.0-live-vision] - Gemini Live Video Pipeline
*   **Feature:** Implemented an automatic ~2-second delta screenshot feed directly into the Gemini Live session, providing the agent with persistent visual context. Full pipeline verified end-to-end.

### [v2.5.1-pin-auth-verified] & [v2.5.0-pin-auth] - Fallback Auth System
*   **Feature:** Added a PIN authentication gate as a fallback mechanism for all PWAs and backend endpoints. Registered securely in Firestore.

### [v2.4.0-reproducibility] & [v2.3.0-docs] - Documentation & Launch Prep
*   **Docs:** Added `REPRODUCIBILITY.md`, security roadmap, updated `README.md`, and finalized architecture diagrams. Repository prepared for public viewing.

### [v2.2.0-public-launch] & [v2.1.0-landing-page] - Public Deployment
*   **Feature:** Deployed the Landing Page and Setup Page to `aegis.projectalpha.in`. System is now accessible for public demo.

### [v2.0.0-multi-user] - Architecture Overhaul
*   **Feature:** Migrated to a multi-user architecture. Firestore schemas are now scoped securely per user. Added `X-User-ID` headers across all backend endpoints. Added `install.sh` for easy setup.

### [v1.9.0-cicd] - Deployment Automation
*   **Feature:** Implemented prebuilt Docker images and CI/CD pipelines for deployment.

### [v1.7.2-schema-aware], [v1.7.1-seven-toolkits], [v1.7.0-seven-toolkits] - The API Integration Era
*   **Feature:** Implemented and stabilized 7 Composio toolkits (Gmail, Calendar, Docs, Sheets, Slides, Tasks, GitHub). Added schema-aware argument filling. (Note: These features were later deprecated in `v2.7.0` in favor of Native ComputerUse).

### [v1.6.0-faceid-working] - Biometric Auth Success
*   **Feature:** Full end-to-end working demonstration of Face ID out-of-band authentication on the iPhone companion app for "RED" tier actions.

### [v1.5.0-pwas-working], [v1.4.0-all-pwas-live], [v1.3.0-pwa-pivot] - The Move to PWAs
*   **Feature:** Deployed macOS PWA and Mobile PWA. All four services (Backend, Dashboard, Mac App, Mobile App) are now live. Shelved native macOS/iOS apps in favor of cross-platform Progressive Web Apps.

### [v1.0.0-websocket] - Real-time Communication
*   **Feature:** Implemented a local WebSocket server (`ws://localhost:8765`) to stream real-time UI events, state changes, and audio waveforms from the Python agent to the Mac PWA.

### [v0.8.0-aegis] - Rebranding
*   **Feature:** Officially rebranded the project to "Aegis" — The Trusted Pilot for the Agentic Era.

### [v0.7.0-domains-live], [v0.6.0-domain], [v0.5.0-all-tiers] - Core Security Model Verification
*   **Feature:** All three tiers (GREEN: Silent, YELLOW: Confirm, RED: Biometric) are fully operational and verified end-to-end.

### [v0.4.0-full-stack] & [v0.3.0-dashboard] - Dashboard & Cloud Run
*   **Feature:** Deployed the real-time Dashboard PWA and backend to GCP Cloud Run.

### [v0.2.0-gcp] & [v0.1.0-core] - Initial Cloud Architecture
*   **Feature:** Configured core settings and successfully deployed the initial backend structure to Google Cloud Platform.