import asyncio
import base64
import json
import logging
import pyaudio
from google import genai
from google.genai import types
from . import config
from .context import AegisContext
from .gate import gate_action

logger = logging.getLogger("aegis.voice")

SYSTEM_PROMPT = """
You are Aegis, a trusted AI agent that controls the user's Mac computer.

You can hear the user's voice and see their screen in real time.

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
    def __init__(self, context: AegisContext):
        self.context = context
        self.pya = pyaudio.PyAudio()
        self.client = genai.Client(api_key=config.GOOGLE_API_KEY)
        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=SYSTEM_PROMPT,
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

                    if response.data:
                        await asyncio.to_thread(output_stream.write, response.data)

                    if response.tool_call:
                        self.context.is_executing_tool = True
                        logger.info("⏳ Pausing audio input during tool execution...")
                        try:
                            for fn in response.tool_call.function_calls:
                                if fn.name == "execute_action":
                                    action = fn.args.get("action", "")
                                    confirmed = fn.args.get("confirmed", False)
                                    logger.info(f"📥 Received action: '{action}' (confirmed: {confirmed})")

                                    result = await gate_action(action, self.context, pre_confirmed=confirmed)

                                    if result.get("needs_confirmation"):
                                        tool_response = {"result": "ACTION BLOCKED PENDING CONFIRMATION. You MUST ask the user to confirm this action: " + result['speak'] + ". If they say yes, call execute_action again with confirmed=true."}
                                    else:
                                        # Truncate to prevent hitting frame limits on websocket
                                        if "output" in result and result.get("output"):
                                            out_str = str(result["output"])
                                            result["output"] = out_str[:2000] + ("..." if len(out_str) > 2000 else "")
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
        except Exception as e:
            logger.error(f"Error in receive_and_play_loop: {e}")
        finally:
            output_stream.close()

    async def run(self):
        try:
            mic_info = self.pya.get_default_input_device_info()
        except Exception as e:
            logger.error(f"Failed to access default input device: {e}")
            return

        logger.info("🌐 Connecting to Gemini Live API...")
        try:
            async with self.client.aio.live.connect(model=config.GEMINI_LIVE_MODEL, config=self.config) as session:
                self.context.session = session
                logger.info("✅ Connected to Gemini Live API")
                logger.info("🎙️ Aegis is listening...")

                await asyncio.gather(
                    self._send_audio_loop(session, mic_info),
                    self._receive_and_play_loop(session)
                )
        except Exception as e:
            logger.exception(f"Unexpected error in run_aegis: {e}")
        finally:
            self.pya.terminate()
