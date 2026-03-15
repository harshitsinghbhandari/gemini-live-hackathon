import logging
import asyncio
import base64
import wave
import io
from typing import Optional
from google import genai
from google.genai import types
from configs.agent import config

logger = logging.getLogger("aegis.confirmation")

class ConfirmationListener:
    """Manages passive audio collection and intent detection for YELLOW tier actions."""
    def __init__(self):
        self.buffer = io.BytesIO()
        self.is_active = False
        self.lock = asyncio.Lock()
        self.client = genai.Client(api_key=config.GOOGLE_API_KEY)

    async def start_listening(self):
        async with self.lock:
            self.buffer = io.BytesIO() # Reset buffer
            self.is_active = True
            logger.info("👂 Passive confirmation listener started.")

    def stop_listening(self):
        self.is_active = False
        logger.info("👂 Passive confirmation listener stopped.")

    def add_audio(self, data: bytes):
        if self.is_active:
            self.buffer.write(data)

    async def detect_intent(self) -> Optional[bool]:
        """Sends the collected audio to Gemini Flash to detect YES/NO intent."""
        if self.buffer.getbuffer().nbytes < 1024:
            logger.warning("👂 Not enough audio collected for intent detection.")
            return None

        audio_data = self.buffer.getvalue()
        
        # Create a proper WAV in memory for Gemini if needed, 
        # but Gemini GenAI can handle raw PCM if we specify mime type correctly
        # Actually, it's safer to wrap in a simple WAV header for broad compatibility.
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(config.SEND_SAMPLE_RATE)
            wf.writeframes(audio_data)
        
        try:
            logger.info(f"👂 Analyzing {len(audio_data)} bytes of confirmation audio...")
            response = await self.client.aio.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(
                        data=wav_buffer.getvalue(),
                        mime_type="audio/wav"
                    ),
                    "The user just spoke to confirm an action. Did they say something affirmative (YES, GO, CONTINUE, PROCEED, SURE, OKAY) or negative (NO, STOP, CANCEL, DON'T)? Respond ONLY with 'YES' or 'NO'. If unsure or silent, respond 'NO'."
                ]
            )
            
            text = response.text.upper()
            if "YES" in text:
                logger.info("✅ Passive intent detected: YES")
                return True
            logger.info("❌ Passive intent detected: NO")
            return False
        except Exception as e:
            logger.error(f"👂 Intent detection failed: {e}")
            return False
