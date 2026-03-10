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

class AegisVoiceAgent:
    def __init__(self, context: AegisContext, status_callback=None, text_only_mode=False):
        self.context = context
        self.status_callback = status_callback
        self.pya = pyaudio.PyAudio()
        self.client = genai.Client(api_key=config.GOOGLE_API_KEY)
        self.alive = True
        self.text_only_mode = text_only_mode
        
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

    async def _send_to_session(self, session, **kwargs):
        """Drops media frames if a tool is currently executing, model is responding, or session is dead."""
        if not self.alive:
            logger.debug("Skipping send: session not alive")
            return
            
        # The Turn Gate: Strictly block all media if the model is busy or a tool is running
        if self.context.is_executing_tool:
            logger.debug("Skipping media send: tool execution in progress")
            return 
        if self.context.is_model_responding:
            logger.debug("Skipping media send: model is currently thinking/responding (Turn Gate)")
            return
        
        try:
            # Added detailed logging for the payload structure
            keys = list(kwargs.keys())
            for k in keys:
                val = kwargs[k]
                if isinstance(val, types.Blob):
                    logger.debug(f"Sending {k}: {val.mime_type} ({len(val.data)} bytes)")
                else:
                    logger.debug(f"Sending {k}: {type(val)}")
            
            await session.send_realtime_input(**kwargs)
        except Exception as e:
            logger.error(f"❌ Media send failed: {e}")
            logger.error(f"   Payload keys: {keys}")
            if "1008" in str(e) or "Requested entity was not found" in str(e):
                logger.error("🛑 Session fatal error detected. Stopping loops.")
                self.alive = False

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
            logger.info("🎙️ Audio loop active")
            while self.alive:
                if self.context.is_executing_tool or self.context.is_model_responding:
                    await asyncio.sleep(0.1)
                    continue

                data = await asyncio.to_thread(stream.read, config.CHUNK_SIZE, False)
                
                # Waveform broadcast (mic amplitude)
                import struct
                shorts = struct.unpack(f"{len(data)//2}h", data)
                peak = max(abs(s) for s in shorts) / 32768.0
                ws_server.broadcast("waveform", value=round(peak, 3))

                await self._send_to_session(
                    session,
                    audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={config.SEND_SAMPLE_RATE}")
                )
        except Exception as e:
            if self.alive:
                logger.error(f"Error in send_audio_loop: {e}")
        finally:
            logger.info("🎙️ Audio loop finishing")
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
            logger.info("🔊 Receive loop active")
            while self.alive:
                async for response in session.receive():
                    if not self.alive:
                        break
                    
                    # Log raw response structure (concise)
                    logger.debug(f"📥 Received from Gemini: {response}")
                    
                    if response.server_content:
                        # If the server sends content, it's either starting or continuing a response
                        self.context.is_model_responding = True
                        
                        if response.server_content.interrupted:
                            logger.info("⚡ Interrupted")
                            # If interrupted, the turn is essentially reset
                            self.context.is_model_responding = False
                            self.context.is_executing_tool = False
                            self._update_status("listening")
                            # Immediately stop playback
                            await asyncio.to_thread(output_stream.stop_stream)
                            await asyncio.to_thread(output_stream.start_stream)
                            continue

                        if response.server_content.turn_complete:
                            logger.info("🏁 Turn complete")
                            self.context.is_model_responding = False
                            self.context.is_executing_tool = False
                            self._update_status("listening")
                            logger.info("🎙️ Resuming audio input (Turn complete)")
                            ws_server.broadcast("turn_complete")

                        # Skip non-audio server content (text/thought parts from thinking models)
                        if response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if getattr(part, "thought", False):
                                    logger.info(f"💭 Thought: {part.text}")
                                    ws_server.broadcast("thought", value=part.text)
                                    continue
                                if part.text:
                                    logger.info(f"📝 Text: {part.text}")
                                    ws_server.broadcast("text", value=part.text)
                                    continue
                                if part.inline_data:
                                    # logger.debug(f"🎵 Audio chunk: {len(part.inline_data.data)} bytes")
                                    await asyncio.to_thread(output_stream.write, part.inline_data.data)

                    if response.tool_call:
                        # Tools also count as the model being "busy"
                        self.context.is_model_responding = True
                        self.context.is_executing_tool = True
                        self._update_status("executing")
                        logger.info("⏳ Pausing media input during tool execution...")
                        try:
                            function_responses = []
                            if response.tool_call.function_calls:
                                for fn in response.tool_call.function_calls:
                                    logger.info(f"🛠️ Tool Requested: {fn.name} (ID: {fn.id})")
                                    logger.info(f"   Args: {json.dumps(fn.args, indent=2)}")

                                    # 1. Specialized Schema Request
                                    if fn.name == "get_tool_schema":
                                        requested = fn.args.get("tool_names", [])
                                        schemas = get_schemas_for(requested, self.context)
                                        logger.info(f"   Schemas found for: {list(schemas.keys())}")
                                        function_responses.append(types.Part(
                                            function_response=types.FunctionResponse(
                                                id=fn.id, name=fn.name, response={"result": schemas}
                                            )
                                        ))

                                    # 2. Native ComputerUse (Delegated)
                                    elif fn.name in ["open_web_browser", "navigate", "click_at", "double_click_at", "right_click_at", "drag_and_drop", "scroll", "type_text_at", "key_combination", "wait"]:
                                        logger.info(f"🖥️ Delegating ComputerUse {fn.name}...")
                                        p = await handle_computer_use(fn, self.context, lambda: self._update_status("auth"))
                                        if p: 
                                            logger.info(f"✅ ComputerUse {fn.name} handled")
                                            function_responses.append(p)

                                    # 3. Dynamic Tools (Composio/Screen)
                                    else:
                                        arguments = dict(fn.args) if fn.args else {}
                                        result = await gate_action(
                                            f"Run tool {fn.name} with args {json.dumps(arguments)}",
                                            self.context,
                                            tool_name=fn.name,
                                            tool_args=arguments,
                                            on_auth_request=lambda: self._update_status("auth")
                                        )

                                        if result.get("needs_confirmation"):
                                            tool_response = {"result": "ACTION BLOCKED PENDING CONFIRMATION. You MUST ask the user to confirm: " + result['speak']}
                                        else:
                                            if result.get("blocked") and result.get("tier") == "RED":
                                                self._update_status("blocked")
                                            tool_response = {"result": json.dumps(result)}

                                        shot = capture_screen() if is_screen_tool(fn.name) else None
                                        logger.info(f"   Tool Result: {tool_response.get('result', '')[:200]}...")
                                        
                                        f_resp = types.FunctionResponse(id=fn.id, name=fn.name, response=tool_response)
                                        if shot:
                                            logger.info(f"   Attaching screenshot: {shot['mime_type']} ({len(shot['base64'])} base64 chars)")
                                            f_resp.parts = [types.Part(inline_data=types.Blob(
                                                data=base64.b64decode(shot["base64"]), mime_type=shot["mime_type"]
                                            ))]
                                        function_responses.append(types.Part(function_response=f_resp))

                            if function_responses:
                                logger.info(f"📤 Sending {len(function_responses)} tool responses back to Gemini...")
                                await session.send(input=types.LiveClientToolResponse(
                                    function_responses=[p.function_response for p in function_responses]
                                ))

                        except Exception as e:
                            logger.error(f"Error executing tools: {e}")

        except Exception as e:
            if self.alive:
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
                while self.alive:
                    async with session.get(f"{config.BACKEND_URL}/session/status", timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("is_active") is False:
                                logger.info("🛑 Remote stop signal received.")
                                # Trigger stop by setting an event or closing session
                                if self.context.session:
                                    # This will likely break the loops and trigger finally block
                                    await self.context.session.close()
                                    self.alive = False
                                return
                    # Increased polling interval to 10s to reduce backend load
                    await asyncio.sleep(10)
        except Exception as e:
            if self.alive:
                logger.warning(f"Remote stop check failed: {e}")

    async def _visual_stream_loop(self, session):
        """Periodically sends low-res screenshots to Gemini Live for continuous visual context."""
        logger.info("🎬 Starting visual stream loop...")
        try:
            while self.alive:
                # Skip streaming while a tool is executing to save bandwidth and focus
                if self.context.is_executing_tool:
                    await asyncio.sleep(0.5)
                    continue

                # Capture at a reduced resolution for efficiency (1024x1024 works well for Gemini)
                shot = capture_screen(scale_to=(1024, 1024), quality=50)
                
                # Use 'video' for screenshots; the SDK maps this to the visual track
                await self._send_to_session(
                    session,
                    video=types.Blob(
                        data=base64.b64decode(shot["base64"]), 
                        mime_type=shot["mime_type"] # Keep this as image/jpeg
                    )
                )
                
                # Broad polling interval — 5 seconds is enough for general awareness
                await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            logger.info("🎬 Visual stream loop cancelled.")
        except Exception as e:
            if self.alive:
                logger.error(f"Error in visual_stream_loop: {e}")

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

                tasks = [
                    self._receive_and_play_loop(session),
                    self._visual_stream_loop(session)
                ]
                if not self.text_only_mode:
                    tasks.append(self._send_audio_loop(session, mic_info))
                else:
                    logger.info("ℹ️  Text-only mode: Audio input loop disabled.")

                await asyncio.gather(*tasks)
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