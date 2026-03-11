# Aegis Folder: File Roles and Documentation

This document provides a comprehensive overview of every file within the `aegis` folder, detailing its specific purpose, core functionality, and its role within the Aegis architecture.

---

## Core Logic & Orchestration

### [auth.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/auth.py)
- **Role**: Local Biometric Security Provider.
- **Detailed Purpose**: Interfaces with macOS native LocalAuthentication framework to provide biometric verification (Touch ID/Face ID).
- **Core Functionality**:
    - `request_touch_id(reason, timeout)`: Triggers a native macOS authentication prompt. It uses `pyobjc` to call into the `LocalAuthentication` framework on a background thread.
- **Why it exists**: To provide high-assurance security for "RED" tier actions by verifying the physical presence of the device owner.

### [classifier.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/classifier.py)
- **Role**: AI Security Policy Engine.
- **Detailed Purpose**: Acts as the "brains" of the security system, using Gemini to categorize every proposed action into a risk tier.
- **Core Functionality**:
    - `classify_action(proposed_action, tool_hint)`: Prompt-engineers Gemini to return a JSON categorization (GREEN, YELLOW, RED) based on rigorous security rules.
    - `RISK_PROMPT`: Contains the ruleset defining what constitutes different risk levels for screen interaction.
- **Why it exists**: This file uses LLM reasoning to enforce a consistent security policy across all screen control tools.

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
    - Loads `.env` file for API keys (`GOOGLE_API_KEY`).
    - Defines audio sample rates (16k send, 24k receive).
    - `setup_logging()`: Initializes both human-readable logs (`aegis.log`) and machine-readable audit logs (`aegis_audit.jsonl`).
- **Why it exists**: To avoid hardcoded values and ensure consistent behavior across different environments.

### [context.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/context.py)
- **Role**: Global State Management.
- **Detailed Purpose**: A simple container for tracking the active session and agent status across different loops.
- **Core Functionality**:
    - `AegisContext`: A dataclass storing references to the Gemini Live session and flags like `is_executing_tool`.
- **Why it exists**: Audio, Visual, and Feedback loops run concurrently; this shared context prevents them from stepping on each other.

### [executor.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/executor.py)
- **Role**: Executor Stub.
- **Detailed Purpose**: Provides stubs for previously used search and execute functions.
- **Why it exists**: Maintained as a stub to avoid breaking minimal dependencies, though its previous Composio logic has been removed.

### [gate.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/gate.py)
- **Role**: The Primary Security Gatekeeper.
- **Detailed Purpose**: Orchestrates the entire "Request -> Classify -> Auth -> Execute -> Audit" lifecycle.
- **Core Functionality**:
    - `gate_action(...)`: The entry point for every action. It calls the classifier, checks the tier, triggers auth if needed, and finally hands off to the screen executor.
    - `request_remote_auth(...)`: Polls the cloud backend for approval from the Aegis Mobile App.
    - `audit_logger`: Formats every action and its result into a persistent JSONL audit trail.
- **Why it exists**: To ensure that NO action can be taken on the user's computer without passing through the security engine and being recorded.

### [helper_server.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/helper_server.py)
- **Role**: Agent Life-cycle Manager (FastAPI).
- **Detailed Purpose**: Provides a local REST API that allows the Web/PWA interface to manage the background Python process.
- **Core Functionality**:
    - `/start`: Spawns the main agent process (`main.py`).
    - `/stop`: Gracefully terminates the agent.
    - `/status`: Checks if the agent is alive.
- **Why it exists**: Bridges the gap between the Web UI and the underlying Python automation.

### [screen_executor.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/screen_executor.py)
- **Role**: Native Desktop Driver.
- **Detailed Purpose**: Handles low-latency local actions like mouse clicks, keyboard typing, and screen scraping.
- **Core Functionality**:
    - `SCREEN_TOOL_DECLARATIONS`: The JSON schemas sent to Gemini so it knows how to use the mouse and keyboard.
    - `smart_plan(goal)`: Sends a screenshot to Gemini Pro to generate a multi-step execution plan.
    - `verify_ui_state(expected)`: Fast visual check to confirm the current screen matches the expected step.
    - `plan_complete()`: Marks an autonomous plan as finished, re-enabling the microphone.
- **Why it exists**: Ensures maximum speed and reliability for desktop-specific tasks while providing high-level reasoning and autonomous loops.

### [tool_manager.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/tool_manager.py)
- **Role**: Capability Registry.
- **Detailed Purpose**: Manages what the AI "knows" it can do by loading tool definitions.
- **Core Functionality**:
    - `load_tools()`: Reads from `tools.json`.
- **Why it exists**: Maintains a local registry of available tools for the agent.

### [voice.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/voice.py)
- **Role**: Multimodal Hub (The Heart of Aegis).
- **Detailed Purpose**: Manages the high-speed duplex stream of audio and video with the Gemini Live API.
- **Core Functionality**:
    - `_send_audio_loop`: Streams mic data to Gemini.
    - `_receive_and_play_loop`: Plays Gemini's voice and intercepts tool calls.
    - `_visual_stream_loop`: Periodically sends screenshots to give the AI "vision."
- **Why it exists**: Provides the seamless coordinating Real-time Audio, Vision, and Action experience.

### [ws_server.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/ws_server.py)
- **Role**: Real-time Telemetry Server.
- **Detailed Purpose**: A WebSocket server that broadcasts the agent's internal state to any connected UI.
- **Core Functionality**:
    - `broadcast(event, value, data)`: Sends events like "waveform", "thought", "action", and "status".
- **Why it exists**: Allows the Dashboard and Menu Bar app to show real-time visualizations.

---

## Screen Interaction Utilities (`aegis/screen/`)

### [capture.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/screen/capture.py)
- **Purpose**: High-speed screen capture.
- **Functionality**: Uses `mss` for ultra-fast frame grabbing and `Pillow` for JPEG optimization.

### [cursor.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/screen/cursor.py)
- **Purpose**: Mouse manipulation.
- **Functionality**: Wraps `pyautogui` for moving, clicking, dragging, and scrolling.

### [type.py](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/screen/type.py)
- **Purpose**: Keyboard manipulation.
- **Functionality**: Uses the system clipboard (`pbcopy`) to "type" text reliably. Handles hotkeys and sensitive data clearing.

---

## Data & Initialization

### [`tools.json`](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/tools.json)
- **Role**: Local Tool Schema Cache.
- **Detailed Purpose**: Stores JSON schemas for the native screen control tools.
- **Why it exists**: Allows Aegis to "know" its capabilities instantly and fetch specific schemas reducing startup latency.

### [`__init__.py`](file:///Users/harshitsinghbhandari/Downloads/main-quests/gemini-live-hackathon/aegis/__init__.py)
- **Role**: Package Entry Point.
- **Detailed Purpose**: Marks the `aegis` directory as a Python package.
