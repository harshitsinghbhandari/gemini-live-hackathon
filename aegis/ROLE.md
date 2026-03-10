# Aegis Folder: File Roles and Documentation

This document provides a comprehensive overview of every file within the `aegis` folder, detailing its specific purpose, core functionality, and its role within the Aegis architecture.

---

## Core Logic & Orchestration

### [auth.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/auth.py)
- **Role**: Local Biometric Security Provider.
- **Detailed Purpose**: Interfaces with macOS native LocalAuthentication framework to provide biometric verification (Touch ID/Face ID).
- **Core Functionality**:
    - `request_touch_id(reason, timeout)`: Triggers a native macOS authentication prompt. It uses `pyobjc` to call into the `LocalAuthentication` framework on a background thread.
- **Why it exists**: To provide high-assurance security for "RED" tier actions (like deleting data or sending sensitive info) by verifying the physical presence of the device owner.

### [classifier.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/classifier.py)
- **Role**: AI Security Policy Engine.
- **Detailed Purpose**: Acts as the "brains" of the security system, using Gemini to categorize every proposed action into a risk tier.
- **Core Functionality**:
    - `classify_action(proposed_action, tool_hint)`: Prompt-engineers Gemini to return a JSON categorization (GREEN, YELLOW, RED) based on rigorous security rules.
    - `RISK_PROMPT`: Contains the complex ruleset defining what constitutes different risk levels.
- **Why it exists**: Hand-coding security rules for 100+ tools is impossible. This file uses LLM reasoning to enforce a consistent security policy across all integrations.

### [computer_use.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/computer_use.py)
- **Role**: Native Gemini `ComputerUse` Adapter.
- **Detailed Purpose**: Bridges the gap between Gemini's native "Computer Use" tool (0-1000 coordinates) and Aegis's internal desktop automation tools.
- **Core Functionality**:
    - `handle_computer_use(...)`: Intercepts native Gemini function calls (like `click_at`, `navigate`) and routes them through the Aegis `gate_action` system.
    - `denormalize(x, y)`: Converts 0-1000 coordinate system to the actual pixel dimensions of the current hardware display.
- **Why it exists**: To allow Aegis to support Gemini's high-level native desktop control while still enforcing Aegis's specific security gates and audit logging.

### [config.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/config.py)
- **Role**: System Configuration & Initialization.
- **Detailed Purpose**: Centralizes all settings, constants, and environment variable loading.
- **Core Functionality**:
    - Loads `.env` file for API keys (`GOOGLE_API_KEY`, `COMPOSIO_API_KEY`).
    - Defines audio sample rates (16k send, 24k receive).
    - `setup_logging()`: Initializes both human-readable logs (`aegis.log`) and machine-readable audit logs (`aegis_audit.jsonl`).
- **Why it exists**: To avoid hardcoded values and ensure consistent behavior across different environments and deployment stages.

### [context.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/context.py)
- **Role**: Global State Management.
- **Detailed Purpose**: A simple container for tracking the active session and agent status across different loops.
- **Core Functionality**:
    - `AegisContext`: A dataclass storing references to the Gemini Live session, Composio client, and flags like `is_executing_tool`.
- **Why it exists**: Audio, Visual, and Feedback loops run concurrently; this shared context prevents them from stepping on each other (e.g., stops audio capture while the model is speaking).

### [executor.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/executor.py)
- **Role**: External Integration Engine (Composio).
- **Detailed Purpose**: Manages the execution of tools for external apps like Gmail, Google Calendar, GitHub, etc.
- **Core Functionality**:
    - `fill_arguments(...)`: A "smart" argument filler that fetches tool schemas and uses Gemini to translate natural language into perfect JSON arguments.
    - `search_and_execute(...)`: Leverages the Composio Tool Router to find the best tool for a high-level user request.
- **Why it exists**: To connect Aegis to hundreds of real-world apps via Composio while ensuring the data passed to these APIs is accurate and complete.

### [gate.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/gate.py)
- **Role**: The Primary Security Gatekeeper.
- **Detailed Purpose**: The most critical file in the repo; it orchestrates the entire "Request -> Classify -> Auth -> Execute -> Audit" lifecycle.
- **Core Functionality**:
    - `gate_action(...)`: The entry point for every action. It calls the classifier, checks the tier, triggers auth if needed, and finally hands off to an executor.
    - `request_remote_auth(...)`: Polls the cloud backend for approval from the Aegis Mobile App.
    - `audit_logger`: Formats every action and its result into a persistent JSONL audit trail.
- **Why it exists**: To ensure that NO CODE can execute an action on the user's computer without first passing through the security engine and being recorded.

### [helper_server.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/helper_server.py)
- **Role**: Agent Life-cycle Manager (FastAPI).
- **Detailed Purpose**: Provides a local REST API that allows the Web/PWA interface to manage the background Python process.
- **Core Functionality**:
    - `/start`: Spawns the main agent process (`main.py`).
    - `/stop`: Gracefully terminates the agent.
    - `/status`: Checks if the agent is alive and reports uptime.
- **Why it exists**: Users shouldn't have to touch the terminal. This server bridges the gap between the beautiful Web UI and the underlying Python automation.

### [screen_executor.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/screen_executor.py)
- **Role**: Native Desktop Driver.
- **Detailed Purpose**: Handles low-latency local actions like mouse clicks, keyboard typing, and screen scraping.
- **Core Functionality**:
    - `SCREEN_TOOL_DECLARATIONS`: The JSON schemas sent to Gemini so it knows how to use the mouse and keyboard.
    - `run_screen_agent(...)`: A mini agentic loop for complex UI automation tasks.
    - `execute_screen_action(...)`: Routes calls to the low-level `pyautogui` wrappers.
- **Why it exists**: Bypassing the network for local UI actions ensures maximum speed and reliability for desktop-specific tasks.

### [tool_manager.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/tool_manager.py)
- **Role**: Schema & Capability Registry.
- **Detailed Purpose**: Manages what the AI "knows" it can do by loading tool definitions.
- **Core Functionality**:
    - `load_tools()`: Reads from `tools.json`.
    - `get_schemas_for(...)`: Provides full JSON schemas to Gemini Live session when requested.
- **Why it exists**: Gemini Live works best when it can "lazy-load" tool schemas as needed, rather than being overwhelmed with 100+ tools at connection time.

### [voice.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/voice.py)
- **Role**: Multimodal Hub (The Heart of Aegis).
- **Detailed Purpose**: Manages the high-speed duplex stream of audio and video with the Gemini Live API.
- **Core Functionality**:
    - `_send_audio_loop`: Streams mic data to Gemini.
    - `_receive_and_play_loop`: Plays Gemini's voice and intercepts tool calls.
    - `_visual_stream_loop`: Periodically sends screenshots to give the AI "vision."
    - **Turn Gating**: Ensures media input stops during tool execution or model responding to prevent policy violations (Status 1008).
- **Why it exists**: To provide the "Live" experience by coordinating Real-time Audio, Vision, and Action in a single seamless loop.

### [ws_server.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/ws_server.py)
- **Role**: Real-time Telemetry Server.
- **Detailed Purpose**: A WebSocket server that broadcasts the agent's internal state to any connected UI.
- **Core Functionality**:
    - `broadcast(event, value, data)`: Sends events like "waveform", "thought", "action", and "status".
- **Why it exists**: Allows the Dashboard and Menu Bar app to show real-time visualizations (like the voice ripple or action cards) of what the agent is thinking and doing.

---

## Screen Interaction Utilities (`aegis/screen/`)

### [capture.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/screen/capture.py)
- **Purpose**: High-speed screen capture.
- **Functionality**: Uses `mss` for ultra-fast frame grabbing and `Pillow` for JPEG optimization.
- **Architectural Role**: Provides the "Eyes" of the system, optimizing images to save bandwidth and LLM tokens.

### [cursor.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/screen/cursor.py)
- **Purpose**: Mouse manipulation.
- **Functionality**: Wraps `pyautogui` for moving, clicking, dragging, and scrolling. Includes failsafe logic.
- **Architectural Role**: The "Hands" of the system for spatial UI interaction.

### [type.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/screen/type.py)
- **Purpose**: Keyboard manipulation.
- **Functionality**: Uses the system clipboard (`pbcopy`) to "type" text reliably, effectively bypassing layout issues and ensuring speed. Handles hotkeys and sensitive data clearing.
- **Architectural Role**: The primary method for text input and application control.

---

## Data & Initialization

### [`tools.json`](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/tools.json)
- **Role**: Local Tool Schema Cache.
- **Detailed Purpose**: Stores pre-fetched JSON schemas for the most common Composio and native tools.
- **Why it exists**: Sending 100+ tool schemas to Gemini on every connection is slow and hits token limits. This file allows Aegis to "know" its capabilities instantly and fetch specific schemas only when needed, significantly reducing startup latency.

### [`__init__.py`](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/__init__.py)
- **Role**: Package Entry Point.
- **Detailed Purpose**: Marks the `aegis` directory as a Python package.
- **Why it exists**: Enables other modules (like the root `main.py`) to import from the `aegis` folder (e.g., `from aegis import voice`).
