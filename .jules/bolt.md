## 2024-05-18 - PyAutoGUI & MSS Blocking Calls
**Learning:** `pyautogui` functions (especially with `duration`) and `mss` / `PIL.Image` screen captures are synchronous and CPU-bound. Calling them directly inside async execution functions blocks the event loop, preventing concurrent connections like SSE streams from firing.
**Action:** Use `await asyncio.to_thread()` to offload these functions to the default ThreadPoolExecutor.

## 2024-05-18 - Gemini Client Instantiation Overhead
**Learning:** The `google.genai.Client` does internal setup and validation. Instantiating it per tool execution or per classification adds unnecessary overhead. Since `config.GOOGLE_API_KEY` is stable and the client's `aio` functionality is designed for concurrency, it should be reused.
**Action:** Hoist the `genai.Client` instantiation to a module-level variable (`_client`) and use a getter function to access the single instance.
