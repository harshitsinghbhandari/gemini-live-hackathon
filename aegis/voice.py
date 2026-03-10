import asyncio
import base64
import json
import logging
import pyaudio
from google import genai
from google.genai import types
from google.genai.types import (
    ComputerUse,
    Environment,
    ThinkingConfig,
    Tool,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
)
from . import config
from .context import AegisContext
from .gate import gate_action
import os
from .screen_executor import is_screen_tool, SCREEN_TOOL_DECLARATIONS
from .screen.capture import capture_screen
from . import ws_server

logger = logging.getLogger("aegis.voice")

def load_tools():
    path = os.path.join(os.path.dirname(__file__), "tools.json")
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load tools.json: {e}")
    return {}

TOOLS = load_tools()

def get_tool_names_prompt():
    screen_names = [t["name"] for t in SCREEN_TOOL_DECLARATIONS]
    composio_names = list(TOOLS.keys())
    all_names = screen_names + composio_names
    return "Available tools:\n" + "\n".join(f"  {n}" for n in all_names)

def get_schemas_for(tool_names: list, context: AegisContext = None) -> dict:
    screen_map = {t["name"]: t for t in SCREEN_TOOL_DECLARATIONS}
    result = {}
    for name in tool_names:
        if name in TOOLS:
            result[name] = TOOLS[name]
        elif name in screen_map:
            result[name] = screen_map[name]
        elif context and context.composio:
            try:
                # Dynamic fallback to fetch schema from Composio
                import httpx
                url = f"https://backend.composio.dev/api/v3/tools/{name.lower()}?toolkit_versions=latest"
                headers = {"x-api-key": config.COMPOSIO_API_KEY}
                with httpx.Client() as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        schema = data.get("input_parameters") or data.get("expected_schema")
                        if schema:
                            result[name] = {
                                "name": name,
                                "description": data.get("description", ""),
                                "parameters": schema
                            }
                            continue
                result[name] = {"error": f"Unknown tool: {name}"}
            except Exception as e:
                logger.error(f"Failed to fetch schema for {name} from Composio: {e}")
                result[name] = {"error": f"Failed to fetch schema for {name}: {e}"}
        else:
            result[name] = {"error": f"Unknown tool: {name}"}
    return result

SYSTEM_PROMPT = """
You are Aegis, a trusted AI agent that controls the user's Mac computer.

You can hear the user's voice and see the user's screen via screenshots.
When the user asks you to do something:
1. Identify which tool(s) you need.
2. If you need to interact with the screen (click, type, scroll, etc.), use the `computer_use` tool.
3. If you need a specific capability from the list below and don't have the schema, call `get_tool_schema([tool_name])`.
4. Once you have the schema, call the tool with the correct arguments.

{tool_list}

You speak naturally and concisely. You always tell the user:
- What you're about to do
- Whether it needs their fingerprint (RED actions)
- What happened after execution

You are calm, trustworthy, and never do anything without being clear about it.
Keep responses short and conversational — this is voice, not text.
"""

class AegisVoiceAgent:
    def __init__(self, context: AegisContext, status_callback=None):
        self.context = context
        self.status_callback = status_callback
        self.pya = pyaudio.PyAudio()
        self.client = genai.Client(api_key=config.GOOGLE_API_KEY)
        
        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=SYSTEM_PROMPT.format(tool_list=get_tool_names_prompt()),
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(
                        voice_name=config.VOICE_NAME,
                    )
                ),
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    prefix_padding_ms=200,
                    silence_duration_ms=500,
                ),
            ),
            thinking_config=ThinkingConfig(include_thoughts=True),
            tools=[
                Tool(
                    computer_use=ComputerUse(
                        environment=Environment.ENVIRONMENT_BROWSER,
                    )
                ),
                {
                    "function_declarations": [
                        {
                            "name": "get_tool_schema",
                            "description": "Get the parameter schema for one or more tools before calling them. Be reasonable — only request schemas you actually need.",
                            "parameters": {
                                "type": "OBJECT",
                                "properties": {
                                    "tool_names": {
                                        "type": "ARRAY",
                                        "items": {"type": "STRING"},
                                        "description": "List of tool names to get schemas for"
                                    }
                                },
                                "required": ["tool_names"]
                            }
                        }
                    ]
                }
            ]
        )


    def _update_status(self, status: str):
        """Thread-safe status update forwarded to the menu bar and WebSocket UI."""
        if self.status_callback:
            try:
                self.status_callback(status)
            except Exception:
                pass
        
        # Broadcast to WebSocket UI
        ws_server.broadcast("status", value=status)

    def _denormalize(self, x: int, y: int) -> tuple[int, int]:
        """Convert Gemini 0-1000 coordinates to Aegis capture scale (1470, 956)"""
        # capture.py uses (1470, 956) as default scale_to
        target_w, target_h = 1470, 956
        # Ensure coordinates are within 0-1000 range as per ComputerUse spec
        nx = max(0, min(1000, x))
        ny = max(0, min(1000, y))
        return int(nx / 1000 * target_w), int(ny / 1000 * target_h)

    async def _send_audio_loop(self, session, mic_info):
        """Captures mic and sends to Gemini"""
        stream = await asyncio.to_thread(
            self.pya.open,
            format=pyaudio.paInt16,
            channels=1,
            rate=config.SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=config.CHUNK_SIZE
        )

        try:
            while True:
                if self.context.is_executing_tool:
                    await asyncio.sleep(0.1)
                    continue

                data = await asyncio.to_thread(stream.read, config.CHUNK_SIZE, False)
                
                # Waveform broadcast (mic amplitude)
                import struct
                shorts = struct.unpack(f"{len(data)//2}h", data)
                peak = max(abs(s) for s in shorts) / 32768.0
                ws_server.broadcast("waveform", value=round(peak, 3))

                await session.send_realtime_input(
                    audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={config.SEND_SAMPLE_RATE}")
                )
        except Exception as e:
            logger.error(f"Error in send_audio_loop: {e}")
        finally:
            stream.close()

    async def _receive_and_play_loop(self, session):
        """Receives audio response and plays it + handles tool calls"""
        output_stream = await asyncio.to_thread(
            self.pya.open,
            format=pyaudio.paInt16,
            channels=1,
            rate=config.RECEIVE_SAMPLE_RATE,
            output=True
        )

        try:
            while True:
                async for response in session.receive():
                    if response.server_content:
                        if response.server_content.interrupted:
                            logger.info("⚡ Interrupted")
                            # Immediately stop playback
                            await asyncio.to_thread(output_stream.stop_stream)
                            await asyncio.to_thread(output_stream.start_stream)
                            continue

                        if response.server_content.turn_complete:
                            logger.info("🏁 Turn complete")
                            ws_server.broadcast("turn_complete")

                        # Skip non-audio server content (text/thought parts from thinking models)
                        if response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if getattr(part, "thought", False):
                                    logger.debug(f"💭 Thinking: {part.text}")
                                    ws_server.broadcast("thought", value=part.text)
                                    continue
                                if part.text:
                                    logger.debug(f"📝 Model text: {part.text[:80]}")
                                    ws_server.broadcast("text", value=part.text)
                                    continue
                                if part.inline_data:
                                    await asyncio.to_thread(output_stream.write, part.inline_data.data)

                    if response.tool_call:
                        self.context.is_executing_tool = True
                        self._update_status("executing")
                        logger.info("⏳ Pausing audio input during tool execution...")
                        try:
                            function_responses = []
                            
                            # Handle standard function calls (get_tool_schema, Composio tools)
                            if response.tool_call.function_calls:
                                for fn in response.tool_call.function_calls:
                                    if fn.name == "get_tool_schema":
                                        requested = fn.args.get("tool_names", [])
                                        logger.info(f"🔍 Gemini requested schemas for: {requested}")
                                        schemas = get_schemas_for(requested, self.context)
                                        logger.info(f"📤 Returning schemas for: {list(schemas.keys())}")
                                        
                                        function_responses.append(types.Part(
                                            function_response=types.FunctionResponse(
                                                id=fn.id,
                                                name=fn.name,
                                                response={"result": schemas}
                                            )
                                        ))

                                    else:
                                        # Real tool call (dynamic)
                                        tool_name = fn.name
                                        arguments = dict(fn.args) if fn.args else {}
                                        logger.info(f"📥 Received tool call: {tool_name} with args: {arguments}")

                                        simulated_action = f"Run tool {tool_name} with arguments {json.dumps(arguments)}"
                                        
                                        result = await gate_action(
                                            simulated_action, self.context,
                                            tool_name=tool_name,
                                            tool_args=arguments,
                                            on_auth_request=lambda: self._update_status("auth")
                                        )

                                        if result.get("needs_confirmation"):
                                            tool_response = {"result": "ACTION BLOCKED PENDING CONFIRMATION. You MUST ask the user to confirm this action: " + result['speak'] + ". If they say yes, call the tool again with the same arguments."}
                                        else:
                                            if result.get("blocked") and result.get("tier") == "RED":
                                                self._update_status("blocked")
                                            tool_response = {"result": json.dumps(result)}

                                        shot = capture_screen() if is_screen_tool(fn.name) else None

                                        function_responses.append(types.Part(
                                            function_response=types.FunctionResponse(
                                                id=fn.id,
                                                name=fn.name,
                                                response=tool_response,
                                                parts=[types.FunctionResponsePart(
                                                    inline_data=types.FunctionResponseBlob(
                                                        data=base64.b64decode(shot["base64"]),
                                                        mime_type=shot["mime_type"]
                                                    )
                                                )] if shot else []
                                            )
                                        ))

                            # Handle native ComputerUse calls
                            if response.tool_call.computer_use:
                                cu = response.tool_call.computer_use
                                for action in cu.actions:
                                    logger.info(f"🖥️  Received ComputerUse action: {action.name}")
                                    
                                    # Map native ComputerUse to Aegis Screen Tools
                                    mapped_tool = None
                                    mapped_args = {}
                                    
                                    if action.name == "open_web_browser":
                                        mapped_tool = "SCREEN_HOTKEY"
                                        mapped_args = {"keys": ["command", "space"]} # Simulate opening Spotlight or browser
                                    elif action.name == "navigate":
                                        mapped_tool = "SCREEN_TYPE"
                                        mapped_args = {"text": action.args["url"], "press_enter": True}
                                    elif action.name == "click_at":
                                        mapped_tool = "SCREEN_CLICK"
                                        mapped_args["x"], mapped_args["y"] = self._denormalize(action.args["x"], action.args["y"])
                                    elif action.name == "double_click_at":
                                        mapped_tool = "SCREEN_DOUBLE_CLICK"
                                        mapped_args["x"], mapped_args["y"] = self._denormalize(action.args["x"], action.args["y"])
                                    elif action.name == "right_click_at":
                                        mapped_tool = "SCREEN_RIGHT_CLICK"
                                        mapped_args["x"], mapped_args["y"] = self._denormalize(action.args["x"], action.args["y"])
                                    elif action.name == "drag_and_drop":
                                        mapped_tool = "SCREEN_DRAG"
                                        mapped_args["x1"], mapped_args["y1"] = self._denormalize(action.args["x1"], action.args["y1"])
                                        mapped_args["x2"], mapped_args["y2"] = self._denormalize(action.args["x2"], action.args["y2"])
                                    elif action.name == "scroll":
                                        mapped_tool = "SCREEN_SCROLL"
                                        mapped_args["x"], mapped_args["y"] = self._denormalize(action.args["x"], action.args["y"])
                                        mapped_args["clicks"] = -10 if action.args["direction"] == "down" else 10
                                    elif action.name == "type_text_at":
                                        mapped_tool = "SCREEN_TYPE"
                                        tx, ty = self._denormalize(action.args["x"], action.args["y"])
                                        # Gating the implicit click before typing
                                        await gate_action(f"Click at ({tx}, {ty})", self.context, tool_name="SCREEN_CLICK", tool_args={"x": tx, "y": ty})
                                        mapped_args = {"text": action.args["text"]}
                                    elif action.name == "key_combination":
                                        mapped_tool = "SCREEN_HOTKEY"
                                        mapped_args = {"keys": action.args["keys"]}
                                    elif action.name == "wait":
                                        mapped_tool = "SCREEN_MOVE"
                                        mapped_args = {"x": 735, "y": 478}
                                    
                                    if mapped_tool:
                                        simulated_action = f"ComputerUse: {action.name} with args {json.dumps(action.args)}"
                                        result = await gate_action(
                                            simulated_action, self.context,
                                            tool_name=mapped_tool,
                                            tool_args=mapped_args,
                                            on_auth_request=lambda: self._update_status("auth")
                                        )
                                        
                                        shot = capture_screen()
                                        response_payload = {"url": "macOS Desktop"}
                                        if not result.get("success"):
                                            response_payload["error"] = result.get("error", "Action blocked or failed")
                                        
                                        function_responses.append(types.Part(
                                            function_response=types.FunctionResponse(
                                                id=action.id,
                                                name=action.name,
                                                response=response_payload,
                                                parts=[types.FunctionResponsePart(
                                                    inline_data=types.FunctionResponseBlob(
                                                        data=base64.b64decode(shot["base64"]),
                                                        mime_type=shot["mime_type"]
                                                    )
                                                )]
                                            )
                                        ))

                            if function_responses:
                                await session.send(input=types.LiveClientToolResponse(
                                    function_responses=[p.function_response for p in function_responses]
                                ))

                        except Exception as e:
                            logger.error(f"Error executing tools: {e}")
                        finally:
                            self.context.is_executing_tool = False
                            self._update_status("listening")
                            logger.info("🎙️ Resuming audio input...")

        except Exception as e:
            logger.error(f"Error in receive_and_play_loop: {e}")
        finally:
            self._update_status("idle")
            output_stream.close()

    async def _check_remote_stop(self):
        """Polls backend to see if session should stop (e.g. from iOS kill switch)"""
        import aiohttp
        try:
            headers = {"X-User-ID": config.USER_ID}
            async with aiohttp.ClientSession(headers=headers) as session:
                while True:
                    async with session.get(f"{config.BACKEND_URL}/session/status", timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("is_active") is False:
                                logger.info("🛑 Remote stop signal received.")
                                # Trigger stop by setting an event or closing session
                                if self.context.session:
                                    # This will likely break the loops and trigger finally block
                                    await self.context.session.close()
                                return
                    # Increased polling interval to 10s to reduce backend load
                    await asyncio.sleep(10)
        except Exception as e:
            logger.warning(f"Remote stop check failed: {e}")

    async def run(self):
        # Notify backend that session has started
        from .gate import post_to_backend
        await post_to_backend("/session/status", {"is_active": True}, await_response=True)

        # Start remote stop check
        asyncio.create_task(self._check_remote_stop())

        # Start WebSocket server in background
        server = ws_server.get_server()
        asyncio.create_task(server.start())

        try:
            mic_info = self.pya.get_default_input_device_info()
        except Exception as e:
            logger.error(f"Failed to access default input device: {e}")
            self._update_status("error")
            return

        logger.info("🌐 Connecting to Gemini Live API...")
        try:
            async with self.client.aio.live.connect(model=config.GEMINI_LIVE_MODEL, config=self.config) as session:
                self.context.session = session
                logger.info("✅ Connected to Gemini Live API")
                logger.info("🎙️ Aegis is listening...")
                self._update_status("listening")
                ws_server.broadcast("session_started")

                await asyncio.gather(
                    self._send_audio_loop(session, mic_info),
                    self._receive_and_play_loop(session)
                )
        except Exception as e:
            logger.exception(f"Unexpected error in run_aegis: {e}")
            self._update_status("error")
            raise
        finally:
            self._update_status("idle")
            ws_server.broadcast("session_ended")
            # Notify backend that session has ended
            from .gate import post_to_backend
            await post_to_backend("/session/status", {"is_active": False})
            self.pya.terminate()


async def run_aegis(status_callback=None, on_agent_ready=None):
    """Top-level entry point for menu bar and other callers."""
    from .config import USER_ID, COMPOSIO_API_KEY
    from composio import Composio

    # Pre-initialize Composio to avoid delay on first tool execution
    composio_client = None
    try:
        composio_client = Composio(api_key=COMPOSIO_API_KEY)
        logger.info("✅ Composio initialized")
    except Exception as e:
        logger.error(f"Failed to pre-initialize Composio: {e}")

    context = AegisContext(user_id=USER_ID, composio=composio_client)
    agent = AegisVoiceAgent(context, status_callback=status_callback)

    if on_agent_ready:
        on_agent_ready(agent)

    await agent.run()
