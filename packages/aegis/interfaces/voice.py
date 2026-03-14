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
from configs.agent import config
from aegis.runtime.context import AegisContext, SessionState
from aegis.utils.latency import checkpoint, flush_summary
from aegis.utils.session_recorder import recorder
from aegis.agent.gate import gate_action
import os
from aegis.runtime.screen_executor import is_screen_tool, get_current_view
from aegis.tools.declarations import get_screen_tool_declarations
from aegis.perception.screen.capture import capture_screen
from aegis.perception.screen.ocr import ocr_background_loop
from aegis.interfaces import ws_server
from aegis.runtime.tool_manager import get_schemas_for
from aegis.computer_use import handle_computer_use
from configs.agent.config import prompt

logger = logging.getLogger("aegis.voice")

class SessionBridge:
    """Bridge for communication between hardware loops and Gemini Live session."""
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=100)

    def put_nowait(self, item):
        """Put an item in the queue, dropping old items if full."""
        checkpoint("bridge", f"put_{item['type']}")
        try:
            self.queue.put_nowait(item)
        except asyncio.QueueFull:
            try:
                checkpoint("bridge", "queue_overflow_drop_oldest")
                self.queue.get_nowait()
                self.queue.put_nowait(item)
            except Exception as e:
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
        self.send_lock = asyncio.Lock()
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
            }
        ]
        # Include custom screen tools in core
        SCREEN_TOOL_DECLARATIONS = get_screen_tool_declarations()
        
        core_function_declarations.extend(SCREEN_TOOL_DECLARATIONS)

        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=prompt.VOICE_SYSTEM_PROMPT,
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
                {
                    "function_declarations": SCREEN_TOOL_DECLARATIONS
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
    def _purge_media_queue(self):
        """Remove all pending audio/video from the queue immediately."""
        checkpoint("bridge", "purge_media_queue_start")
        purged = 0
        while not self.bridge.queue.empty():
            try:
                item = self.bridge.queue.get_nowait()
                if item["type"] in ("audio", "video"):
                    purged += 1
                else:
                    # Put non-media items (like tool responses) back!
                    # Actually, better to use a separate queue for tools to avoid this.
                    pass
                self.bridge.queue.task_done()
            except asyncio.QueueEmpty:
                break
        if purged > 0:
            checkpoint("bridge", f"purged_{purged}_items")
            logger.debug(f"🧹 Purged {purged} stale media packets to prevent 1008.")
        checkpoint("bridge", "purge_media_queue_end")

    async def _send_to_session(self, **kwargs):
        """Directly sends media if in listening state, bypassing the queue delay."""
        if not self.alive or self.context.state != SessionState.LISTENING:
            return
        
        checkpoint("session", "send_to_session_start")
        session = self.context.session
        if not session:
            # Fallback for early hardware loop starts
            if "audio" in kwargs:
                checkpoint("bridge", "fallback_audio_to_queue")
                self.bridge.put_nowait({"type": "audio", "data": kwargs["audio"]})
            if "video" in kwargs:
                checkpoint("bridge", "fallback_video_to_queue")
                self.bridge.put_nowait({"type": "video", "data": kwargs["video"]})
            return

        try:
            async with self.send_lock:
                if "audio" in kwargs:
                    checkpoint("audio", f"direct_send_start_{kwargs['audio']}")
                    recorder.record_sent_audio(kwargs["audio"].data)
                    await session.send_realtime_input(audio=kwargs["audio"])
                    checkpoint("audio", "direct_send_end")
                if "video" in kwargs:
                    checkpoint("video", f"direct_send_start_{kwargs['video']}")
                    recorder.record_image(kwargs["video"].data)
                    await session.send_realtime_input(video=kwargs["video"])
                    checkpoint("video", "direct_send_end")
        except Exception as e:
            checkpoint("session", f"direct_send_error: {type(e).__name__}")
            if self.alive:
                logger.debug(f"Media send suppressed or failed: {e}")
        finally:
            checkpoint("session", "send_to_session_end")
    async def _sender_loop(self, session):
        checkpoint("system", "sender_loop_start")
        while self.alive:
            try:
                # 1. Use a shorter timeout to stay responsive
                item = await asyncio.wait_for(self.bridge.queue.get(), timeout=0.05)
                checkpoint("bridge", f"get_{item['type']}")

                # 2. THE HARD GATE: Drop media if model is BUSY or EXECUTING
                # Gemini 1008 happens if audio arrives when model has already started a tool call.
                if item["type"] in ("audio", "video"):
                    if self.context.state != SessionState.LISTENING:
                        checkpoint("bridge", "drop_media_busy")
                        self.bridge.queue.task_done()
                        continue # Drop the frame entirely

                # 3. TYPE-SPECIFIC EXECUTION
                if item["type"] == "audio":
                    checkpoint("audio", "queue_send_start")
                    recorder.record_sent_audio(item["data"].data)
                    await session.send_realtime_input(audio=item["data"])
                    checkpoint("audio", "queue_send_end")
                    
                elif item["type"] == "video":
                    # Ensure you use 'video' parameter for single frames in this SDK version
                    checkpoint("video", "queue_send_start")
                    recorder.record_image(item["data"].data)
                    await session.send_realtime_input(video=item["data"])
                    checkpoint("video", "queue_send_end")
                    
                elif item["type"] == "tool_response":
                    checkpoint("tool", "send_response_start")
                    logger.info(item)
                    logger.info(f"📤 Sending {len(item['data'])} tool responses...")
                    async with self.send_lock:
                        await session.send(input=types.LiveClientToolResponse(function_responses=item["data"]))
                    logger.info("Tool response sent")
                    checkpoint("tool", "response_sent")
                        # Re-add: Send accompanying media (screenshots) if present
                    if "media" in item and item["media"]:
                        checkpoint("tool", f"sending_{len(item['media'])}_media_blobs")
                        for blob in item["media"]:
                            # Send via realtime input to avoid 1008 policy violation with LiveClientContent
                            await session.send_realtime_input(video=blob)
                        checkpoint("tool", "media_blobs_sent")

                self.bridge.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                checkpoint("system", f"sender_loop_error: {type(e).__name__}")
                logger.error(f"Sender loop error: {e}")
                if "1008" in str(e):
                    logger.error("Sender loop policy violation 1008")
                    self.alive = False
        checkpoint("system", "sender_loop_end")
    async def _send_audio_loop(self, mic_info):
        """Captures mic and sends to bridge"""
        checkpoint("audio", "audio_loop_init")
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
            checkpoint("audio", "audio_loop_active")
            while self.alive:
                data = await asyncio.to_thread(stream.read, config.CHUNK_SIZE, False)
                checkpoint("audio", "chunk_read")
                import struct
                shorts = struct.unpack(f"{len(data)//2}h", data)
                peak = max(abs(s) for s in shorts) / 32768.0
                ws_server.broadcast("waveform", value=round(peak, 3))
                await self._send_to_session(
                    audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={config.SEND_SAMPLE_RATE}")
                )
                checkpoint("audio", "chunk_processed")
        except Exception as e:
            checkpoint("audio", f"audio_loop_error: {type(e).__name__}")
            if self.alive:
                logger.error(f"Error in send_audio_loop: {e}")
        finally:
            checkpoint("audio", "audio_loop_finishing")
            logger.info("🎙️ Audio loop finishing")
            stream.close()
    async def _receive_and_play_loop(self, session):
        """Receives response and plays audio + handles tool calls"""
        checkpoint("audio", "output_loop_init")
        output_stream = await asyncio.to_thread(
            self.pya.open,
            format=pyaudio.paInt16,
            channels=1,
            rate=config.RECEIVE_SAMPLE_RATE,
            output=True
        )

        try:
            logger.info("🔊 Receive loop active")
            checkpoint("session", "receive_loop_active")
            while self.alive:
                logger.info("Waiting for response...")
                async for response in session.receive():
                    checkpoint("llm", "response_pkg_received")
                    # 1. EMERGENCY LOCK: Check for tool calls immediately
                    if response.tool_call:
                        checkpoint("tool", "call_detected_emergent")
                        logger.info("🛠️ Tool call detected")
                        self.context.state = SessionState.EXECUTING
                        logger.info("Purging media queue...")
                        self._purge_media_queue()
                        logger.info("Updating status to executing...")
                        self._update_status("executing")

                    # logger.info(f"🤖 Response: {response}")
                    if not self.alive:
                        logger.info("Not alive, breaking...")
                        break
                    
                    if response.session_resumption_update:
                        logger.info(f"🤖 Session resumption update: {response.session_resumption_update}")
                        update = response.session_resumption_update
                        if update.resumable and update.new_handle:
                            self.context.resumption_handle = update.new_handle
                            logger.info("Captured resumption handle")
                    if response.server_content:
                        # logger.info(f"🤖 Server content: {response.server_content}")
                        self.context.state = SessionState.BUSY
                        if response.server_content.interrupted:
                            checkpoint("llm", "interrupted")
                            logger.info("⚡ Interrupted")
                            self.context.state = SessionState.LISTENING
                            self._update_status("listening")
                            await asyncio.to_thread(output_stream.stop_stream)
                            await asyncio.to_thread(output_stream.start_stream)
                            continue

                        if response.server_content.turn_complete:
                            checkpoint("llm", "turn_complete")
                            ws_server.broadcast("turn_complete")
                            logger.info("🏁 Turn complete")
                            self.context.state = SessionState.LISTENING
                            self._update_status("listening")
                            

                        if response.server_content.model_turn:
                            checkpoint("llm", "model_turn_pkg")
                            # logger.info(f"🤖 Model turn: {response.server_content.model_turn}")
                            for part in response.server_content.model_turn.parts:
                                if getattr(part, "thought", False):
                                    checkpoint("llm", "thought_packet")
                                    ws_server.broadcast("thought", value=part.text)
                                    continue
                                if part.text:
                                    checkpoint("llm", "text_packet")
                                    ws_server.broadcast("text", value=part.text)
                                    continue
                                if part.inline_data:
                                    checkpoint("audio", "pcm_pcm_packet")
                                    recorder.record_received_audio(part.inline_data.data)
                                    await asyncio.to_thread(output_stream.write, part.inline_data.data)
                    if response.tool_call:
                        checkpoint("tool", "process_call_batch")
                        logger.info(f"🤖 Tool call: {response.tool_call}")
                        try:
                            function_responses = []
                            media_blobs = []
                            if response.tool_call.function_calls:
                                checkpoint("tool", f"calls_count_{len(response.tool_call.function_calls)}")
                                logger.info(f"🤖 Function calls: {response.tool_call.function_calls}")
                                for fn in response.tool_call.function_calls:
                                    checkpoint("tool", f"exec_start_{fn.name}")
                                    logger.info(f"🛠️ Tool Requested: {fn.name} (ID: {fn.id})")
                                    if False:
                                        pass
                                    else:
                                        arguments = dict(fn.args) if fn.args else {}
                                        checkpoint("tool", f"gate_action_start_{fn.name}")
                                        result = await gate_action(
                                            f"Run tool {fn.name} with args {json.dumps(arguments)}",
                                            self.context,
                                            tool_name=fn.name,
                                            tool_args=arguments,
                                            on_auth_request=lambda: self._update_status("auth"),
                                            call_id=fn.id
                                        )
                                        checkpoint("tool", f"gate_action_end_{fn.name}")
                                        
                                        if result.get("needs_confirmation"):
                                            checkpoint("tool", "needs_confirmation")
                                            logger.info("🤖 Needs confirmation")
                                            tool_response = {"result": "ACTION BLOCKED PENDING CONFIRMATION. You MUST ask the user to confirm: " + result['speak']}
                                        else:
                                            logger.info("🤖 No confirmation needed")
                                            if result.get("blocked") and result.get("tier") == "RED":
                                                checkpoint("tool", "red_tier_blocked")
                                                self._update_status("blocked")

                                        # Update Context with Smart Plan
                                        if fn.name == "smart_plan" and result.get("success"):
                                            checkpoint("tool", "smart_plan_captured")
                                            plan = result.get("plan")
                                            if isinstance(plan, list):
                                                self.context.execution_plan = plan
                                                self.context.plan_index = 0
                                                self.context.plan_halted = False
                                                self.context.verification_passed = False
                                                logger.info(f"📋 Plan captured: {len(self.context.execution_plan)} steps")
                                            else:
                                                logger.warning(f"⚠️  Smart Plan returned invalid plan format: {type(plan)}")

                                        if fn.name == "plan_complete":
                                            checkpoint("tool", "plan_complete_signal")
                                            self.context.execution_plan = None
                                            self.context.plan_index = 0
                                            self.context.verification_passed = False
                                            logger.info("🏁 Plan completed and cleared.")

                                        # ─── Phase 3: Automated Verification Gate ───
                                        # If we are executing a plan step (and it's not the smart_plan/verify
                                        # tools themselves), and the step has a "verify" criterion, run it.
                                        plan_verify_criteria = None
                                        if (
                                            self.context.execution_plan
                                            and not self.context.plan_halted
                                            and fn.name not in ("smart_plan", "verify_ui_state", "plan_complete", "screen_capture", "screen_read")
                                            and result.get("success")
                                        ):
                                            current_step_idx = self.context.plan_index
                                            plan = self.context.execution_plan
                                            
                                            if current_step_idx < len(plan):
                                                current_step = plan[current_step_idx]
                                                plan_verify_criteria = current_step.get("verify")

                                        if plan_verify_criteria:
                                            checkpoint("tool", "auto_verify_start")
                                            logger.info(f"🔍 Auto-verifying step {self.context.plan_index + 1}: '{plan_verify_criteria}'")
                                            verify_result = await gate_action(
                                                f"Verify UI state: {plan_verify_criteria}",
                                                self.context,
                                                tool_name="verify_ui_state",
                                                tool_args={"expected": plan_verify_criteria},
                                                call_id=f"auto_verify_{fn.id}"
                                            )
                                            checkpoint("tool", "auto_verify_end")
                                            verified = verify_result.get("output", {})
                                            # verify_ui_state returns {"verified": bool, ...} nested in output
                                            if isinstance(verified, dict):
                                                is_success = verified.get("verified", False)
                                            else:
                                                # Parse from raw result string
                                                is_success = "true" in str(verify_result.get("output", "")).lower() or verify_result.get("success", False)

                                            if is_success:
                                                checkpoint("tool", "verify_passed")
                                                logger.info(f"✅ Verification passed for step {self.context.plan_index + 1}")
                                                self.context.verification_passed = True
                                                self.context.plan_index += 1
                                                tool_response = {"result": json.dumps(result) + f'\n[SYSTEM: Verification PASSED for step {self.context.plan_index}. Criterion met: "{plan_verify_criteria}". Proceed to the next step.]'}
                                            else:
                                                checkpoint("tool", "verify_failed")
                                                reason = verify_result.get("output", {})
                                                if isinstance(reason, dict):
                                                    reason = reason.get("reason", "Unknown")
                                                ws_server.broadcast("plan_halted", data={"step": self.context.plan_index + 1, "criterion": plan_verify_criteria, "reason": str(reason)})
                                                logger.warning(f"❌ Verification FAILED for step {self.context.plan_index + 1}: {reason}")
                                                self.context.plan_halted = True
                                                self.context.plan_halt_reason = str(reason)
                                                self.context.execution_plan = None
                                                self.context.verification_passed = False
                                                tool_response = {"result": f'[SYSTEM: VERIFICATION FAILED. The screen does NOT show: "{plan_verify_criteria}". Reason: {reason}. HALT the plan. Tell the user EXACTLY what step failed and what you saw. Do NOT say Done, Finished, or Complete. Ask the user how to proceed.]'}
                                        else:
                                            tool_response = {"result": json.dumps(result)}

                                    f_resp = types.FunctionResponse(id=fn.id, name=fn.name, response=tool_response)
                                    # Settling Delay: Let the UI finish animating before capturing response screenshot
                                    checkpoint("system", "settling_delay_start")
                                    await asyncio.sleep(config.SETTLING_DELAY)
                                    checkpoint("system", "settling_delay_end")
                                    checkpoint("video", "response_capture_start")
                                    shot = get_current_view() # Fresh screenshot (full or cropped) after tool
                                    checkpoint("video", "response_capture_end")
                                    function_responses.append(f_resp)
                                    if shot:
                                        blob = types.Blob(
                                            data=base64.b64decode(shot["base64"]), mime_type=shot["mime_type"]
                                        )
                                        recorder.record_image(blob.data)
                                        media_blobs.append(blob)
                                    checkpoint("tool", f"exec_end_{fn.name}")

                            if function_responses:
                                checkpoint("bridge", "put_tool_response")
                                self.bridge.put_nowait({
                                    "type": "tool_response",
                                    "data": function_responses,
                                    "media": media_blobs
                                })

                        except Exception as e:
                            checkpoint("tool", f"error: {type(e).__name__}")
                            logger.error(f"Error executing tools: {e}")

        except Exception as e:
            checkpoint("session", f"receive_play_error: {type(e).__name__}")
            if self.alive:
                logger.error(f"Error in receive_and_play_loop: {e}")
                if "1000" in str(e) or "cancelled" in str(e).lower():
                    return "reconnect"
        finally:
            checkpoint("audio", "output_loop_cleanup")
            self._update_status("idle")
            output_stream.close()
    async def _visual_stream_loop(self):
        """Sends foveated (active window) screenshots only on change or state transition to THINKING."""
        from aegis.perception.screen.capture import capture_active_window
        from aegis.tools.context import window_state as screen_window_state
        logger.info("🎬 Starting foveated delta-based visual stream loop...")
        checkpoint("video", "visual_stream_loop_start")
        last_hash = None
        last_state = self.context.state

        try:
            while self.alive:
                # Use active-window foveated capture; falls back to full screen automatically
                checkpoint("video", "capture_active_window_start")
                shot = capture_active_window(padding=config.VISION_PADDING, quality=40)
                checkpoint("video", "capture_active_window_end")

                # Sync the crop origin into screen_executor's window_state so
                # get_noisy_center can remap Gemini's 0-1000 coords correctly.
                origin_x = shot.get("origin_x", 0)
                origin_y = shot.get("origin_y", 0)
                is_cropped = origin_x != 0 or origin_y != 0
                if is_cropped:
                    screen_window_state.crop_origin_x = origin_x
                    screen_window_state.crop_origin_y = origin_y
                    screen_window_state.crop_width = shot["width"]
                    screen_window_state.crop_height = shot["height"]
                    checkpoint("video", "state_cropped")
                else:
                    # Full screen — reset any lingering crop state
                    screen_window_state.crop_origin_x = 0
                    screen_window_state.crop_origin_y = 0
                    screen_window_state.crop_width = None
                    screen_window_state.crop_height = None
                    checkpoint("video", "state_fullscreen")

                current_hash = hashlib.md5(shot["base64"].encode()).hexdigest()
                state_transitioned_to_thinking = (self.context.state == SessionState.THINKING and last_state != SessionState.THINKING)
                
                if current_hash != last_hash or state_transitioned_to_thinking:
                    if current_hash != last_hash:
                        checkpoint("video", "change_detected")
                        logger.info("📸 Sending new screenshot, because of hash change")
                    else:
                        checkpoint("video", "thinking_transition_force_send")
                        logger.info("📸 Sending new screenshot, because of state transition to thinking")
                    
                    await self._send_to_session(
                        video=types.Blob(
                            data=base64.b64decode(shot["base64"]),
                            mime_type=shot["mime_type"]
                        )
                    )
                    checkpoint("video", "frame_sent_to_session")
                    last_hash = current_hash

                last_state = self.context.state
                await asyncio.sleep(5.0)
        except Exception as e:
            checkpoint("video", f"loop_error: {type(e).__name__}")
            if self.alive:
                logger.error(f"Error in visual_stream_loop: {e}")
        checkpoint("video", "visual_stream_loop_end")
    async def run(self):
        checkpoint("system", "agent_run_start")
        from aegis.agent.gate import post_to_backend
        await post_to_backend("/session/status", {"is_active": True}, await_response=True)
        checkpoint("system", "status_posted_active")
        asyncio.create_task(self._check_remote_stop())
        server = ws_server.get_server()
        asyncio.create_task(server.start())
        checkpoint("system", "ws_server_start")
        # Start OCR background loop
        asyncio.create_task(ocr_background_loop(self.context), name="OCRBackgroundLoop")
        checkpoint("system", "ocr_loop_spawned")
        try:
            mic_info = self.pya.get_default_input_device_info()
            checkpoint("audio", f"mic_detected_{mic_info['name']}")
        except Exception as e:
            checkpoint("audio", "mic_detection_failed")
            logger.error(f"Failed to access default input device: {e}")
            self._update_status("error")
            return
        reconnect_count = 0
        max_reconnects = 5

        while reconnect_count < max_reconnects and self.alive:
            checkpoint("session", f"connect_attempt_{reconnect_count+1}")
            logger.info(f"🌐 Connecting (attempt {reconnect_count+1})...")
            session_config = self.config
            if self.context.resumption_handle:
                checkpoint("session", "using_resumption_handle")
                session_config.session_resumption = types.SessionResumptionConfig(
                    handle=self.context.resumption_handle
                )

            try:
                async with self.client.aio.live.connect(model=config.GEMINI_LIVE_MODEL, config=session_config) as session:
                    self.context.session = session
                    checkpoint("session", "connected_to_gemini")
                    logger.info("✅ Connected to Gemini Live")
                    self._update_status("listening")
                    ws_server.broadcast("session_started")

                    tasks = [
                        self._sender_loop(session),
                        self._receive_and_play_loop(session),
                        self._visual_stream_loop()
                    ]
                    if not self.text_only_mode:
                        checkpoint("audio", "spawning_audio_send_loop")
                        tasks.append(self._send_audio_loop(mic_info))

                    checkpoint("system", "all_tasks_gathering")
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    checkpoint("system", "tasks_halted")

                    should_reconnect = False
                    for res in results:
                        if res == "reconnect":
                            checkpoint("session", "reconnect_requested_by_task")
                            should_reconnect = True
                        if isinstance(res, Exception):
                            checkpoint("system", f"task_exception_{type(res).__name__}")
                            logger.error(f"Task exception: {res}")
                            if "1008" in str(res): should_reconnect = True

                    if not should_reconnect: 
                        checkpoint("session", "breaking_reconnect_loop")
                        break
                    
                    checkpoint("session", "preparing_reconnect")

            except Exception as e:
                checkpoint("session", f"connect_exception_{type(e).__name__}")
                logger.error(f"Session error: {e}")
                if "1008" in str(e): logger.error("1008 policy error")

            reconnect_count += 1
            await asyncio.sleep(1)

        checkpoint("system", "agent_run_cleanup")
        self._update_status("idle")
        ws_server.broadcast("session_ended")
        await post_to_backend("/session/status", {"is_active": False})
        checkpoint("system", "status_posted_inactive")

        # Cleanup browser
        try:
            from aegis.browser_manager import get_browser_manager
            manager = await get_browser_manager()
            await manager.close()
            checkpoint("system", "browser_closed")
        except Exception as e:
            logger.debug(f"Browser cleanup failed: {e}")

        self.pya.terminate()
        checkpoint("system", "pyaudio_terminated")
        
        # Flush the full latency report
        flush_summary(f"voice_agent_{int(time.time())}")
        recorder.finalize()

    async def _check_remote_stop(self):
        import aiohttp
        checkpoint("system", "remote_stop_check_init")
        try:
            headers = {"X-User-ID": config.USER_ID}
            async with aiohttp.ClientSession(headers=headers) as session:
                while self.alive:
                    checkpoint("system", "poll_remote_status")
                    async with session.get(f"{config.BACKEND_URL}/session/status", timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("is_active") is False:
                                checkpoint("system", "remote_stop_received")
                                logger.info("🛑 Remote stop received")
                                self.alive = False
                                return
                    await asyncio.sleep(10)
        except Exception as e:
            checkpoint("system", f"remote_stop_poll_error: {type(e).__name__}")
            if self.alive: logger.warning(f"Remote stop check failed: {e}")

async def run_aegis(status_callback=None, on_agent_ready=None):
    checkpoint("system", "run_aegis_entry")
    from configs.agent.config import USER_ID
    context = AegisContext(user_id=USER_ID)
    agent = AegisVoiceAgent(context, status_callback=status_callback)
    if on_agent_ready: on_agent_ready(agent)
    await agent.run()
    checkpoint("system", "run_aegis_exit")
