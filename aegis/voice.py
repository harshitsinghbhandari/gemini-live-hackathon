import asyncio
import base64
import json
import logging
import pyaudio
import time
import hashlib
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
from .context import AegisContext, SessionState
from .gate import gate_action
import os
from .screen_executor import is_screen_tool, SCREEN_TOOL_DECLARATIONS
from .screen.capture import capture_screen
from . import ws_server
from .tool_manager import get_schemas_for, get_tool_names_prompt
from .computer_use import handle_computer_use

logger = logging.getLogger("aegis.voice")

SYSTEM_PROMPT = """
You are Aegis, a trusted AI agent controlling this Mac.
You have vision (screenshots) and tools.

CORE TOOLS:
1. computer_use (click, type, navigate, etc.)
2. gmail (read/send emails)
3. get_tool_schema (fetch schemas for other tools like Calendar, GitHub, etc.)

If you need a tool not in CORE, call `get_tool_schema(["tool_name"])` first.
Be concise. Tell the user what you are doing.
"""

class SessionBridge:
    """Bridge for communication between hardware loops and Gemini Live session."""
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=100)

    def put_nowait(self, item):
        """Put an item in the queue, dropping old items if full."""
        try:
            self.queue.put_nowait(item)
        except asyncio.QueueFull:
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(item)
            except Exception:
                pass

class AegisVoiceAgent:
    def __init__(self, context: AegisContext, status_callback=None, text_only_mode=False):
        self.context = context
        self.status_callback = status_callback
        self.pya = pyaudio.PyAudio()
        self.client = genai.Client(api_key=config.GOOGLE_API_KEY)
        self.alive = True
        self.text_only_mode = text_only_mode
        self.bridge = SessionBridge()
        
        # Define Core Tools for initial config
        core_function_declarations = [
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
            },
            {
                "name": "gmail_list_messages",
                "description": "List Gmail messages",
                "parameters": {"type": "OBJECT", "properties": {}}
            }
        ]
        # Include custom screen tools in core
        core_function_declarations.extend(SCREEN_TOOL_DECLARATIONS)

        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=SYSTEM_PROMPT,
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
            context_window_compression=types.ContextWindowCompressionConfig(
                trigger_tokens=100000,
                sliding_window=types.SlidingWindow(target_tokens=80000),
            ),
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
                    "function_declarations": core_function_declarations
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

    async def _send_to_session(self, **kwargs):
        """Puts media into the bridge queue instead of direct sending."""
        if not self.alive:
            return
            
        if "audio" in kwargs:
            self.bridge.put_nowait({"type": "audio", "data": kwargs["audio"]})
        if "video" in kwargs:
            self.bridge.put_nowait({"type": "video", "data": kwargs["video"]})

    async def _sender_loop(self, session):
        """Central loop to send everything from bridge queue to Gemini."""
        while self.alive:
            try:
                item = await asyncio.wait_for(self.bridge.queue.get(), timeout=0.1)

                # Hardware Turn Gate: Strictly drop audio/video if not listening
                if item["type"] in ("audio", "video") and self.context.state != SessionState.LISTENING:
                    self.bridge.queue.task_done()
                    continue

                if item["type"] == "audio":
                    await session.send_realtime_input(audio=item["data"])
                elif item["type"] == "video":
                    await session.send_realtime_input(video=item["data"])
                elif item["type"] == "tool_response":
                    await session.send_tool_response(function_responses=item["data"])
                    # Send accompanying media as separate ClientContent parts
                    if "media" in item and item["media"]:
                        for blob in item["media"]:
                            await session.send_client_content(
                                turns=types.Content(
                                    role="user",
                                    parts=[types.Part(inline_data=blob)],
                                ),
                                turn_complete=False,
                            )

                self.bridge.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Sender loop error: {e}")
                if "1008" in str(e):
                    logger.error("Sender loop policy violation 1008")
                    self.alive = False

    async def _send_audio_loop(self, mic_info):
        """Captures mic and sends to bridge"""
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
            logger.info("🎙️ Audio loop active")
            while self.alive:
                data = await asyncio.to_thread(stream.read, config.CHUNK_SIZE, False)
                
                import struct
                shorts = struct.unpack(f"{len(data)//2}h", data)
                peak = max(abs(s) for s in shorts) / 32768.0
                ws_server.broadcast("waveform", value=round(peak, 3))

                await self._send_to_session(
                    audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={config.SEND_SAMPLE_RATE}")
                )
        except Exception as e:
            if self.alive:
                logger.error(f"Error in send_audio_loop: {e}")
        finally:
            logger.info("🎙️ Audio loop finishing")
            stream.close()

    async def _receive_and_play_loop(self, session):
        """Receives response and plays audio + handles tool calls"""
        output_stream = await asyncio.to_thread(
            self.pya.open,
            format=pyaudio.paInt16,
            channels=1,
            rate=config.RECEIVE_SAMPLE_RATE,
            output=True
        )

        try:
            logger.info("🔊 Receive loop active")
            while self.alive:
                async for response in session.receive():
                    if not self.alive:
                        break
                    
                    if response.session_resumption_update:
                        update = response.session_resumption_update
                        if update.resumable and update.new_handle:
                            self.context.resumption_handle = update.new_handle
                            logger.info("Captured resumption handle")

                    if response.server_content:
                        self.context.state = SessionState.BUSY
                        
                        if response.server_content.interrupted:
                            logger.info("⚡ Interrupted")
                            self.context.state = SessionState.LISTENING
                            self._update_status("listening")
                            await asyncio.to_thread(output_stream.stop_stream)
                            await asyncio.to_thread(output_stream.start_stream)
                            continue

                        if response.server_content.turn_complete:
                            logger.info("🏁 Turn complete")
                            self.context.state = SessionState.LISTENING
                            self._update_status("listening")
                            ws_server.broadcast("turn_complete")

                        if response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if getattr(part, "thought", False):
                                    ws_server.broadcast("thought", value=part.text)
                                    continue
                                if part.text:
                                    ws_server.broadcast("text", value=part.text)
                                    continue
                                if part.inline_data:
                                    await asyncio.to_thread(output_stream.write, part.inline_data.data)

                    if response.tool_call:
                        self.context.state = SessionState.EXECUTING
                        self._update_status("executing")
                        try:
                            function_responses = []
                            media_blobs = []
                            if response.tool_call.function_calls:
                                for fn in response.tool_call.function_calls:
                                    logger.info(f"🛠️ Tool Requested: {fn.name} (ID: {fn.id})")

                                    if fn.name == "get_tool_schema":
                                        requested = fn.args.get("tool_names", [])
                                        schemas = get_schemas_for(requested, self.context)
                                        f_resp = types.FunctionResponse(
                                            id=fn.id, name=fn.name, response={"result": schemas}
                                        )
                                        shot = None
                                    elif fn.name in ["open_web_browser", "navigate", "click_at", "double_click_at", "right_click_at", "drag_and_drop", "scroll", "type_text_at", "key_combination", "wait"]:
                                        res = await handle_computer_use(fn, self.context, lambda: self._update_status("auth"))
                                        if res:
                                            f_resp, shot = res
                                        else:
                                            f_resp = types.FunctionResponse(id=fn.id, name=fn.name, response={"error": "Handler failed"})
                                            shot = None
                                    else:
                                        arguments = dict(fn.args) if fn.args else {}
                                        result = await gate_action(
                                            f"Run tool {fn.name} with args {json.dumps(arguments)}",
                                            self.context,
                                            tool_name=fn.name,
                                            tool_args=arguments,
                                            on_auth_request=lambda: self._update_status("auth"),
                                            call_id=fn.id
                                        )

                                        if result.get("needs_confirmation"):
                                            tool_response = {"result": "ACTION BLOCKED PENDING CONFIRMATION. You MUST ask the user to confirm: " + result['speak']}
                                        else:
                                            if result.get("blocked") and result.get("tier") == "RED":
                                                self._update_status("blocked")
                                            tool_response = {"result": json.dumps(result)}

                                        f_resp = types.FunctionResponse(id=fn.id, name=fn.name, response=tool_response)
                                        shot = capture_screen() # Fresh screenshot after tool

                                    function_responses.append(f_resp)
                                    if shot:
                                        media_blobs.append(types.Blob(
                                            data=base64.b64decode(shot["base64"]), mime_type=shot["mime_type"]
                                        ))

                            if function_responses:
                                self.bridge.put_nowait({
                                    "type": "tool_response",
                                    "data": function_responses,
                                    "media": media_blobs
                                })

                        except Exception as e:
                            logger.error(f"Error executing tools: {e}")

        except Exception as e:
            if self.alive:
                logger.error(f"Error in receive_and_play_loop: {e}")
                if "1000" in str(e) or "cancelled" in str(e).lower():
                    return "reconnect"
        finally:
            self._update_status("idle")
            output_stream.close()

    async def _visual_stream_loop(self):
        """Sends screenshots only on change or state transition to THINKING."""
        logger.info("🎬 Starting delta-based visual stream loop...")
        last_hash = None
        last_state = self.context.state

        try:
            while self.alive:
                shot = capture_screen(scale_to=(512, 512), quality=40)
                current_hash = hashlib.md5(shot["base64"].encode()).hexdigest()
                
                state_transitioned_to_thinking = (self.context.state == SessionState.THINKING and last_state != SessionState.THINKING)

                if current_hash != last_hash or state_transitioned_to_thinking:
                    await self._send_to_session(
                        video=types.Blob(
                            data=base64.b64decode(shot["base64"]),
                            mime_type=shot["mime_type"]
                        )
                    )
                    last_hash = current_hash
                
                last_state = self.context.state
                await asyncio.sleep(1.0)
        except Exception as e:
            if self.alive:
                logger.error(f"Error in visual_stream_loop: {e}")

    async def run(self):
        from .gate import post_to_backend
        await post_to_backend("/session/status", {"is_active": True}, await_response=True)
        asyncio.create_task(self._check_remote_stop())
        server = ws_server.get_server()
        asyncio.create_task(server.start())

        try:
            mic_info = self.pya.get_default_input_device_info()
        except Exception as e:
            logger.error(f"Failed to access default input device: {e}")
            self._update_status("error")
            return

        reconnect_count = 0
        max_reconnects = 5

        while reconnect_count < max_reconnects and self.alive:
            logger.info(f"🌐 Connecting (attempt {reconnect_count+1})...")

            session_config = self.config
            if self.context.resumption_handle:
                session_config.session_resumption = types.SessionResumptionConfig(
                    handle=self.context.resumption_handle
                )

            try:
                async with self.client.aio.live.connect(model=config.GEMINI_LIVE_MODEL, config=session_config) as session:
                    self.context.session = session
                    logger.info("✅ Connected to Gemini Live")
                    self._update_status("listening")
                    ws_server.broadcast("session_started")

                    tasks = [
                        self._sender_loop(session),
                        self._receive_and_play_loop(session),
                        self._visual_stream_loop()
                    ]
                    if not self.text_only_mode:
                        tasks.append(self._send_audio_loop(mic_info))

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    should_reconnect = False
                    for res in results:
                        if res == "reconnect":
                            should_reconnect = True
                        if isinstance(res, Exception):
                            logger.error(f"Task exception: {res}")
                            if "1008" in str(res): should_reconnect = True

                    if not should_reconnect: break

            except Exception as e:
                logger.error(f"Session error: {e}")
                if "1008" in str(e): logger.error("1008 policy error")

            reconnect_count += 1
            await asyncio.sleep(1)

        self._update_status("idle")
        ws_server.broadcast("session_ended")
        await post_to_backend("/session/status", {"is_active": False})
        self.pya.terminate()

    async def _check_remote_stop(self):
        import aiohttp
        try:
            headers = {"X-User-ID": config.USER_ID}
            async with aiohttp.ClientSession(headers=headers) as session:
                while self.alive:
                    async with session.get(f"{config.BACKEND_URL}/session/status", timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("is_active") is False:
                                logger.info("🛑 Remote stop received")
                                self.alive = False
                                return
                    await asyncio.sleep(10)
        except Exception as e:
            if self.alive: logger.warning(f"Remote stop check failed: {e}")

async def run_aegis(status_callback=None, on_agent_ready=None):
    from .config import USER_ID, COMPOSIO_API_KEY
    from composio import Composio
    composio_client = None
    try:
        composio_client = Composio(api_key=COMPOSIO_API_KEY)
    except Exception as e:
        logger.error(f"Composio init failed: {e}")
    context = AegisContext(user_id=USER_ID, composio=composio_client)
    agent = AegisVoiceAgent(context, status_callback=status_callback)
    if on_agent_ready: on_agent_ready(agent)
    await agent.run()
