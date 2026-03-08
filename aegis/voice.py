import asyncio
import base64
import json
import logging
import pyaudio
from .gate import gate_action
from . import ws_server

logger = logging.getLogger("aegis.voice")

SYSTEM_PROMPT = """
You are Aegis, a trusted AI agent that controls the user's Mac computer.

You can hear the user's voice.

When the user asks you to do something:
1. Understand their intent
2. Decide what action to take
3. Call the execute_action function with a plain english description

You speak naturally and concisely. You always tell the user:
- What you're about to do
- Whether it needs their fingerprint (RED actions)
- What happened after execution

When calling execute_action for the FIRST time on a prompt, ALWAYS set confirmed=False.
If the execute_action returns needs_confirmation=True, ask the user to confirm.
If the user confirms, call execute_action AGAIN with the SAME action and confirmed=True.

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
            system_instruction=SYSTEM_PROMPT,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            tools=[{
                "function_declarations": [{
                    "name": "execute_action",
                    "description": "Execute an action on the user's computer after security check",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "action": {
                                "type": "STRING",
                                "description": "Plain english description of what to do, e.g. 'fetch my latest emails'"
                            },
                            "confirmed": {
                                "type": "BOOLEAN",
                                "description": "ALWAYS false initially. Set to true ONLY if you are re-calling this tool after the user verbally confirmed."
                            }
                        },
                        "required": ["action", "confirmed"]
                    }
                }]
            }]
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
                    if response.server_content and response.server_content.interrupted:
                        logger.info("⚡ Interrupted")
                        continue

                    # Skip non-audio server content (text/thought parts from thinking models)
                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if hasattr(part, 'thought') and part.thought:
                                logger.debug("💭 Skipping thought part")
                                continue
                            if hasattr(part, 'text') and part.text and not part.inline_data:
                                logger.debug(f"📝 Skipping text part: {part.text[:80]}")
                                continue

                    if response.data:
                        await asyncio.to_thread(output_stream.write, response.data)

                    if response.tool_call:
                        self.context.is_executing_tool = True
                        self._update_status("executing")
                        logger.info("⏳ Pausing audio input during tool execution...")
                        try:
                            for fn in response.tool_call.function_calls:
                                if fn.name == "execute_action":
                                    action = fn.args.get("action", "")
                                    confirmed = fn.args.get("confirmed", False)
                                    logger.info(f"📥 Received action: '{action}' (confirmed: {confirmed})")

                                    # Signal auth status for RED tier (gate_action triggers Touch ID)
                                    result = await gate_action(
                                        action, self.context,
                                        pre_confirmed=confirmed,
                                        on_auth_request=lambda: self._update_status("auth")
                                    )

                                    if result.get("needs_confirmation"):
                                        tool_response = {"result": "ACTION BLOCKED PENDING CONFIRMATION. You MUST ask the user to confirm this action: " + result['speak'] + ". If they say yes, call execute_action again with confirmed=true."}
                                    else:
                                        if result.get("blocked") and result.get("tier") == "RED":
                                            self._update_status("blocked")

                                        # Use full result for tool response to Aegis
                                        tool_response = {"result": json.dumps(result)}

                                    logger.info(f"📤 Sending tool response back to Aegis: {tool_response}")
                                    await session.send_tool_response(
                                        function_responses=[types.FunctionResponse(
                                            id=fn.id,
                                            name=fn.name,
                                            response=tool_response
                                        )]
                                    )
                        except Exception as e:
                            logger.error(f"Error processing tool call: {e}")
                        finally:
                            logger.info("▶️ Resuming audio input.")
                            self.context.is_executing_tool = False
                            self._update_status("listening")
        except Exception as e:
            logger.error(f"Error in receive_and_play_loop: {e}")
        finally:
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
