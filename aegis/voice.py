import asyncio
import base64
import json
import logging
import pyaudio
import struct
from google import genai
from google.genai import types
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

class SessionBridge:
    """Bridge for communication between hardware loops and the Gemini session loop."""
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=100)
        self.dropped_frames = 0

    async def put(self, item):
        try:
            self.queue.put_nowait(item)
        except asyncio.QueueFull:
            self.dropped_frames += 1
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
        
    def _get_live_config(self):
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=SYSTEM_PROMPT.format(tool_list=get_tool_names_prompt()),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
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
            thinking_config=types.ThinkingConfig(include_thoughts=True),
            session_resumption=types.SessionResumptionConfig(handle=self.context.session_handle) if self.context.session_handle else None,
            tools=[
                types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER,
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

    async def _sender_loop(self, session):
        """Processes the bridge queue and sends to Gemini."""
        logger.info("📤 Sender loop active")
        try:
            while self.alive:
                item = await self.bridge.queue.get()
                try:
                    if item["type"] == "audio":
                        # Media Gating: Only send if LISTENING
                        if self.context.state == SessionState.LISTENING:
                            await session.send_realtime_input(audio=item["data"])
                    elif item["type"] == "video":
                        # Media Gating: Only send if LISTENING
                        if self.context.state == SessionState.LISTENING:
                            await session.send_realtime_input(video=item["data"])
                    elif item["type"] == "tool_response":
                        await session.send(input=types.LiveClientToolResponse(
                            function_responses=item["data"]
                        ))
                except Exception as e:
                    logger.error(f"❌ Sender error: {e}")
                    if "1008" in str(e):
                        self.alive = False
                finally:
                    self.bridge.queue.task_done()
        except Exception as e:
            logger.error(f"Fatal error in sender_loop: {e}")

    async def _send_audio_loop(self, mic_info):
        """Captures mic and pushes to bridge"""
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
            logger.info("🎙️ Audio capture loop active")
            while self.alive:
                if self.context.state != SessionState.LISTENING:
                    await asyncio.sleep(0.1)
                    continue

                data = await asyncio.to_thread(stream.read, config.CHUNK_SIZE, False)
                
                # Waveform broadcast (mic amplitude)
                shorts = struct.unpack(f"{len(data)//2}h", data)
                peak = max(abs(s) for s in shorts) / 32768.0
                ws_server.broadcast("waveform", value=round(peak, 3))

                await self.bridge.put({
                    "type": "audio",
                    "data": types.Blob(data=data, mime_type=f"audio/pcm;rate={config.SEND_SAMPLE_RATE}")
                })
        except Exception as e:
            if self.alive:
                logger.error(f"Error in send_audio_loop: {e}")
        finally:
            logger.info("🎙️ Audio capture loop finishing")
            stream.close()

    async def _receive_and_play_loop(self, session):
        """Master Controller: Receives audio, handles tools, and manages state."""
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
                    
                    logger.debug(f"📥 Received: {response}")

                    if response.session_resumption_update:
                        update = response.session_resumption_update
                        if update.resumable and update.new_handle:
                            self.context.session_handle = update.new_handle
                            logger.info(f"🔄 Session handle captured: {update.new_handle[:10]}...")

                    if response.server_content:
                        # Transition to THINKING as soon as server content is detected
                        if self.context.state != SessionState.EXECUTING:
                            self.context.state = SessionState.THINKING
                            self._update_status("thinking")
                        
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
                                elif part.text:
                                    ws_server.broadcast("text", value=part.text)
                                elif part.inline_data:
                                    await asyncio.to_thread(output_stream.write, part.inline_data.data)

                    if response.tool_call:
                        self.context.state = SessionState.EXECUTING
                        self._update_status("executing")
                        try:
                            function_responses = []
                            for fn in response.tool_call.function_calls:
                                logger.info(f"🛠️ Tool Requested: {fn.name}")

                                # 1. Specialized Schema Request
                                if fn.name == "get_tool_schema":
                                    requested = fn.args.get("tool_names", [])
                                    schemas = get_schemas_for(requested, self.context)
                                    function_responses.append(types.FunctionResponse(
                                        id=fn.id, name=fn.name, response={"result": schemas}
                                    ))

                                # 2. Native ComputerUse
                                elif fn.name in ["open_web_browser", "navigate", "click_at", "double_click_at", "right_click_at", "drag_and_drop", "scroll", "type_text_at", "key_combination", "wait"]:
                                    p = await handle_computer_use(fn, self.context, lambda: self._update_status("auth"))
                                    if p: function_responses.append(p.function_response)

                                # 3. Dynamic Tools (Composio/Screen)
                                else:
                                    arguments = dict(fn.args) if fn.args else {}
                                    result = await gate_action(
                                        f"Run tool {fn.name}", self.context,
                                        tool_name=fn.name, tool_args=arguments,
                                        on_auth_request=lambda: self._update_status("auth")
                                    )

                                    tool_response = {"result": json.dumps(result)}
                                    if result.get("needs_confirmation"):
                                        tool_response = {"result": "ACTION BLOCKED. Ask user to confirm: " + result['speak']}

                                    shot = capture_screen() # Visual Feedback Loop: Fresh screenshot for EVERY tool
                                    f_resp = types.FunctionResponse(id=fn.id, name=fn.name, response=tool_response)
                                    if shot:
                                        f_resp.parts = [types.Part(inline_data=types.Blob(
                                            data=base64.b64decode(shot["base64"]), mime_type=shot["mime_type"]
                                        ))]
                                    function_responses.append(f_resp)

                            if function_responses:
                                await self.bridge.put({"type": "tool_response", "data": function_responses})

                        except Exception as e:
                            logger.error(f"Error executing tools: {e}")

        except Exception as e:
            if self.alive:
                logger.error(f"Error in receive_and_play_loop: {e}")
        finally:
            self.context.state = SessionState.DEAD
            self._update_status("idle")
            output_stream.close()

    async def _visual_stream_loop(self):
        """Periodically sends low-res screenshots to Gemini."""
        logger.info("🎬 Visual stream loop active")
        try:
            while self.alive:
                if self.context.state != SessionState.LISTENING:
                    await asyncio.sleep(0.5)
                    continue

                shot = capture_screen(scale_to=(1024, 1024), quality=40)
                await self.bridge.put({
                    "type": "video",
                    "data": types.Blob(data=base64.b64decode(shot["base64"]), mime_type=shot["mime_type"])
                })
                await asyncio.sleep(5.0)
        except Exception as e:
            if self.alive: logger.error(f"Visual stream error: {e}")

    async def _check_remote_stop(self):
        import aiohttp
        try:
            headers = {"X-User-ID": self.context.user_id}
            async with aiohttp.ClientSession(headers=headers) as session:
                while self.alive:
                    async with session.get(f"{config.BACKEND_URL}/session/status", timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("is_active") is False:
                                logger.info("🛑 Remote stop signal received.")
                                self.alive = False
                                if self.context.session: await self.context.session.close()
                                return
                    await asyncio.sleep(10)
        except Exception:
            pass

    async def run(self):
        from .gate import post_to_backend
        await post_to_backend("/session/status", {"is_active": True}, await_response=True)
        asyncio.create_task(self._check_remote_stop())
        server = ws_server.get_server()
        asyncio.create_task(server.start())

        try:
            mic_info = self.pya.get_default_input_device_info()
        except Exception:
            self._update_status("error")
            return

        logger.info("🌐 Connecting to Gemini Live API...")
        reconnect_attempts = 0
        while reconnect_attempts < 5 and self.alive:
            try:
                async with self.client.aio.live.connect(model=config.GEMINI_LIVE_MODEL, config=self._get_live_config()) as session:
                    self.context.session = session
                    self.context.state = SessionState.LISTENING
                    self._update_status("listening")
                    ws_server.broadcast("session_started")

                    tasks = [
                        self._sender_loop(session),
                        self._receive_and_play_loop(session),
                        self._visual_stream_loop()
                    ]
                    if not self.text_only_mode:
                        tasks.append(self._send_audio_loop(mic_info))

                    await asyncio.gather(*tasks)
            except Exception as e:
                logger.error(f"Session disconnected: {e}")
                if "1008" in str(e):
                    self.alive = False
                    break
                reconnect_attempts += 1
                await asyncio.sleep(2)

        self.context.state = SessionState.DEAD
        self._update_status("idle")
        ws_server.broadcast("session_ended")
        await post_to_backend("/session/status", {"is_active": False})
        self.pya.terminate()

async def run_aegis(status_callback=None, on_agent_ready=None):
    from .config import USER_ID, COMPOSIO_API_KEY
    from composio import Composio
    composio_client = None
    try:
        composio_client = Composio(api_key=COMPOSIO_API_KEY)
    except Exception: pass

    context = AegisContext(user_id=USER_ID, composio=composio_client)
    agent = AegisVoiceAgent(context, status_callback=status_callback)
    if on_agent_ready: on_agent_ready(agent)
    await agent.run()
