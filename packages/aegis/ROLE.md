# Aegis Folder: File Roles and Documentation

This document provides a comprehensive overview of every file within the `aegis` folder, detailing its specific purpose, core functionality, and its role within the Aegis architecture.

---

## Core Logic & Orchestration

### [auth.py](aegis/auth.py)
- **Role**: Local Biometric Security Provider.
- **Detailed Purpose**: Interfaces with macOS native LocalAuthentication framework to provide biometric verification (Touch ID).
- **Core Functionality**:
    - `request_touch_id(reason, timeout)`: Triggers a native macOS authentication prompt using `pyobjc`.
- **Why it exists**: To provide high-assurance security for "RED" tier actions by verifying the physical presence of the device owner.

### [classifier.py](aegis/classifier.py)
- **Role**: AI Security Policy Engine.
- **Detailed Purpose**: Acts as the "brains" of the security system, using Gemini to categorize every proposed action into a risk tier.
- **Core Functionality**:
    - `classify_action(proposed_action, tool_hint)`: Prompt-engineers Gemini to return a JSON categorization (GREEN, YELLOW, RED) based on security rules.
- **Why it exists**: Enforces a consistent security policy across all screen control tools using LLM reasoning.

### [computer_use.py](aegis/computer_use.py)
- **Role**: Native Gemini `ComputerUse` Adapter.
- **Detailed Purpose**: Bridges the gap between Gemini's native "Computer Use" tool (0-1000 coordinates) and Aegis's internal desktop automation tools.
- **Core Functionality**:
    - `handle_computer_use(...)`: Intercepts native Gemini function calls and routes them through the Aegis `gate_action` system.
    - `denormalize(x, y)`: Converts 0-1000 coordinate system to actual pixel dimensions.
- **Why it exists**: Allows Aegis to support Gemini's high-level native desktop control while enforcing security gates and audit logging.

### [config.py](aegis/config.py)
- **Role**: System Configuration & Initialization.
- **Detailed Purpose**: Centralizes all settings, constants, and environment variable loading.
- **Why it exists**: Ensures consistent behavior across different environments and avoids hardcoded values.

### [context.py](aegis/context.py)
- **Role**: Global State Management.
- **Detailed Purpose**: Container for tracking active session, agent status, and the state machine.
- **Core Functionality**:
    - `SessionState`: Enum defining LISTENING, THINKING, EXECUTING, BUSY.
    - `AegisContext`: Dataclass storing session references and state.
- **Why it exists**: Synchronizes concurrent audio, visual, and feedback loops.

### [gate.py](aegis/gate.py)
- **Role**: The Primary Security Gatekeeper.
- **Detailed Purpose**: Orchestrates the "Request -> Classify -> Auth -> Execute -> Audit" lifecycle.
- **Core Functionality**:
    - `gate_action(...)`: The entry point for every action.
- **Why it exists**: Ensures NO action can be taken without passing through the security engine and being recorded.

### [helper_server.py](aegis/helper_server.py)
- **Role**: Agent Life-cycle Manager (FastAPI).
- **Detailed Purpose**: Local REST API allowing the Mac PWA to manage the background Python agent.
- **Why it exists**: Bridges the Mac PWA UI and the underlying Python automation.

### [screen_executor.py](aegis/screen_executor.py)
- **Role**: Native Desktop Driver.
- **Detailed Purpose**: Executes high-speed screen actions using `pyautogui` and `mss`.
- **Core Functionality**:
    - `SCREEN_TOOL_DECLARATIONS`: JSON schemas for mouse and keyboard tools.
    - `smart_plan(goal)`: Generates multi-step execution plans via Gemini Pro.
- **Why it exists**: Provides the actual "hands" for the agent to control the Mac.

### [voice.py](aegis/voice.py)
- **Role**: Multimodal Hub (The Heart of Aegis).
- **Detailed Purpose**: Manages the high-speed duplex stream of audio and video (screenshots) with the Gemini Live API.
- **Core Functionality**:
    - `_visual_stream_loop`: Continuous delta-based screenshot streaming.
- **Why it exists**: Provides the seamless coordinating Real-time Audio, Vision, and Action experience.

### [ws_server.py](aegis/ws_server.py)
- **Role**: Real-time Telemetry Server.
- **Detailed Purpose**: Broadcasts agent internal state (waveforms, thoughts, status) to connected UIs via WebSockets.
- **Why it exists**: Enables real-time visualizations in the Mac App and Dashboard.

---

## Screen Interaction Utilities (`aegis/screen/`)

### [capture.py](aegis/screen/capture.py)
- **Purpose**: High-speed screen capture using `mss`.

### [cursor.py](aegis/screen/cursor.py)
- **Purpose**: Mouse manipulation wrapping `pyautogui`.

### [type.py](aegis/screen/type.py)
- **Purpose**: Keyboard manipulation using the system clipboard for reliability.
