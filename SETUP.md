# Aegis Full Setup Guide

This guide walks you through the complete process of setting up Aegis on your local macOS environment. You will be configuring the local agent, the cloud backend, and connecting the companion mobile app.

## Prerequisites
Before you begin, ensure you have the following installed on your machine:
*   **macOS** (This is required for native ComputerUse and local Touch ID support.)
*   **Python 3.10 or 3.11** (`python --version`)
*   **Node.js 18+ and npm** (If you intend to run the PWAs locally.)
*   **Google Cloud CLI (`gcloud`)** (If you are deploying the backend yourself.)
*   **A Google Gemini API Key** (Accessible from Google AI Studio.)

---

## 1. Local Agent Setup

### Automatic Setup (Recommended)
1.  Visit the Aegis Setup Page: [https://aegis.projectalpha.in/setup](https://aegis.projectalpha.in/setup)
2.  Follow the prompts to create your profile, input your `GOOGLE_API_KEY`, and create your `AEGIS_PIN`.
3.  The setup page will generate an installation command for your terminal. Run it in the root of the repository.

### Manual Setup
If you prefer not to use the automated script, perform the following steps:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/[your-repo]/aegis.git
    cd aegis
    ```

2.  **Environment Variables:**
    Copy the `.env.example` file and configure your keys.
    ```bash
    cp env/.env.example .env
    ```
    Open `.env` and fill in:
    *   `GOOGLE_API_KEY`: Your Gemini API key.
    *   `USER_ID`: A unique identifier (e.g., your username).
    *   `AEGIS_PIN`: A secure PIN used for fallback authentication.
    *   `BACKEND_URL`: Leave as default (https://apiaegis.projectalpha.in) or your deployed Cloud Run URL.

3.  **Install Python Dependencies:**
    Aegis requires specific dependencies, including `pyautogui` and `mss` for screen capture, and `google-genai` for the Gemini API.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Start the Local Helper Server:**
    The Python helper server handles audio, video streaming, and native computer execution.
    ```bash
    PYTHONPATH=. python3 cmd/agent/run_agent.py
    ```

---

## 2. Connect the Interfaces

1.  **Mac Control Interface:**
    Open the Mac PWA in Chrome or Edge: [https://aegismac.projectalpha.in](https://aegismac.projectalpha.in)
    *   This interface communicates with `run_agent.py` via WebSockets (`ws://localhost:8765`).
    *   Click "Start Aegis" and allow microphone permissions. You should see the audio waveform react to your voice.

2.  **Dashboard:**
    Open [https://aegisdashboard.projectalpha.in](https://aegisdashboard.projectalpha.in)
    *   Enter your `USER_ID`. You will see a real-time stream of audit logs (SSE) as Aegis executes actions on your machine.

3.  **Mobile Companion App (Crucial for RED Actions):**
    Open [https://aegismobile.projectalpha.in](https://aegismobile.projectalpha.in) **on your iPhone Safari**.
    *   Tap the Share icon and select "Add to Home Screen" to install it as a PWA.
    *   Open the newly installed app.
    *   Enter your `USER_ID`.
    *   Click "Register Face ID" to securely bind your device using WebAuthn.
    *   Leave the app open or in the background to receive Red Action auth requests.

---

## 3. Verify End-to-End Operation

Now that everything is running, test the Three-Tier Security Model:

1.  **Green Action (Silent Execution):**
    *   Say aloud to the Mac interface: *"Aegis, take a screenshot and describe what you see."*
    *   *Expected behavior:* The agent should read the screen and reply verbally. No prompts will appear.
2.  **Yellow Action (Verbal Confirmation):**
    *   Say aloud: *"Open a new tab and search for the weather."*
    *   *Expected behavior:* Aegis will classify this as a UI interaction. It will say, "I am about to open a new tab. Is that okay?" Reply "Yes." It will then execute the action.
3.  **Red Action (Biometric Verification):**
    *   Say aloud: *"Aegis, delete the `requirements.txt` file."*
    *   *Expected behavior:* Aegis will classify this as a destructive action. The execution will pause. Your iPhone will display an Auth Request. You must use Face ID on your iPhone to approve it. If approved, the file will be deleted. If denied (or if you don't respond), Aegis will say, "Authentication failed. Action blocked."

## Common Errors & Troubleshooting

*   **"WebSocket Connection Failed" in Mac PWA:** Ensure `cmd/agent/run_agent.py` is running locally. Check terminal logs for port binding errors (`Address already in use`).
*   **Screen Actions Not Working (macOS):** Ensure your Terminal (or VS Code) has **Screen Recording** and **Accessibility** permissions enabled in `System Settings > Privacy & Security`.
*   **Face ID Registration Fails:** Ensure you are accessing the Mobile PWA via `https://` on Safari, and that you have added the site to your Home Screen.
*   **"Authentication failed" immediately:** The backend URL might be misconfigured in your `.env`. Verify it points to the correct deployed backend.