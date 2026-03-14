# Consolidated New Dependencies

| Package | Version | Phase | Purpose | Conflicts With |
|---|---|---|---|---|
| `slowapi` | `0.1.9` | Phase 3 | Rate-limiting sensitive auth routes | None in current requirements |
| `pytest` | `^8.0.0` | Phase 3 | Formal integration tests | Will replace ad-hoc test scripts |
| `pytest-asyncio` | `^0.23.0` | Phase 3 | Async test fixture support | None |

*Conflict check was performed against `services/backend/requirements.txt` and root `requirements.txt`. No version pins collide with the current `fastapi` or `google-genai` versions.*
