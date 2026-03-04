# Changes Documentation

## Modularization
- Reorganized project into a `guardian/` package with clear submodules:
  - `config.py`: Centralized all environment variables, constants, and model names.
  - `context.py`: Introduced `GuardianContext` dataclass to manage session state and dependencies, eliminating global mutable variables.
  - `logging_config.py`: (Integrated into `config.py`) Setup structured logging with rotating file handlers for `guardian.log` and `guardian_audit.jsonl`.
  - `screen.py`: Refactored screen capture with proper error handling and async thread-safe calls.
  - `auth.py`: Refactored Touch ID authentication with better error reporting and timeout handling.
  - `classifier.py`: Modularized action classification with robust Gemini response parsing and fallbacks.
  - `executor.py`: Standardized tool execution with Composio, using consistent return shapes and detailed logging.
  - `gate.py`: Centralized the security gate logic, orchestrating classification, authentication, and execution with a comprehensive audit trail.
  - `voice.py`: Refactored the Gemini Live voice loop into a class-based structure for better maintainability.

## Standardized Patterns
- **Async Consistency**: Standardized the use of `asyncio.to_thread` for blocking I/O (mic, speaker, Touch ID, screen capture).
- **Error Handling**: Wrapped all external calls (Gemini, Composio, Touch ID, Screenshot) in `try/except` blocks.
- **Return Shapes**: Standardized internal return types across modules for predictable behavior.

## Enhanced Logging & Audit
- Replaced all `print()` statements with the Python `logging` module.
- Implemented structured JSONL audit trail for every action, tracking tier, tool, arguments, authentication, and success status.
- Added a rotating file handler to `guardian.log`.

## Bug Fixes & Improvements
- Fixed circular import potential by injecting `GuardianContext` instead of importing modules across each other.
- Handled malformed JSON responses from Gemini with robust parsing and safe fallbacks.
- Improved Touch ID handling for cases where biometrics are unavailable or timed out.
- Handled Composio execution failures gracefully.
