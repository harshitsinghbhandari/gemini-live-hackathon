import asyncio
import base64
import os
import json
import re
import pyaudio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from components.screen_capture import capture_screen
from components.auth_gate import gate_action

load_dotenv()

# Audio config
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "gemini-live-2.5-flash-native-audio"

SYSTEM_PROMPT = """
You are Guardian, a trusted AI agent that controls the user's Mac computer.

You can hear the user's voice and see their screen in real time.

When the user asks you to do something:
1. Understand their intent
2. Decide what action to take
3. Call the execute_action function with a plain english description

You speak naturally and concisely. You always tell the user:
- What you're about to do
- Whether it needs their fingerprint (RED actions)
- What happened after execution

You are calm, trustworthy, and never do anything without being clear about it.
Keep responses short and conversational — this is voice, not text.
"""

pya = pyaudio.PyAudio()

async def run_guardian():
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=SYSTEM_PROMPT,
        tools=[{
            "function_declarations": [{
                "name": "execute_action",
                "description": "Execute an action on the user's computer after security check",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Plain english description of what to do, e.g. 'fetch my latest emails'"
                        }
                    },
                    "required": ["action"]
                }
            }]
        }]
    )
    
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("🎙️  Guardian is listening... (speak now)")
        
        async def send_audio():
            """Captures mic and sends to Gemini"""
            mic_info = pya.get_default_input_device_info()
            stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=mic_info["index"],
                frames_per_buffer=CHUNK_SIZE
            )
            
            # Also send screen every 3 seconds
            screen_task = asyncio.create_task(send_screen_loop(session))
            
            try:
                while True:
                    data = await asyncio.to_thread(
                        stream.read, CHUNK_SIZE, False
                    )
                    await session.send_realtime_input(
                        audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                    )
            finally:
                screen_task.cancel()
                stream.close()
        
        async def send_screen_loop(session):
            """Sends screenshot to Gemini every 3 seconds for context"""
            while True:
                screenshot_b64 = await capture_screen()
                image_data = base64.b64decode(screenshot_b64)
                await session.send_realtime_input(
                    video=types.Blob(data=image_data, mime_type="image/jpeg")
                )
                await asyncio.sleep(3)
        
        async def receive_and_play():
            """Receives audio response and plays it + handles tool calls"""
            output_stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE,
                output=True
            )
            
            try:
                async for response in session.receive():
                    
                    # Handle interruptions gracefully
                    if response.server_content and response.server_content.interrupted:
                        print("⚡ Interrupted")
                        continue
                    
                    # Play audio response
                    if response.data:
                        await asyncio.to_thread(output_stream.write, response.data)
                    
                    # Handle tool calls — this is where Guardian executes actions
                    if response.tool_call:
                        for fn in response.tool_call.function_calls:
                            if fn.name == "execute_action":
                                action = fn.args.get("action", "")
                                print(f"\n🔧 Tool call: {action}")
                                
                                # Run through our auth gate
                                result = await gate_action(action)
                                
                                # Send result back to Gemini so it can speak the outcome
                                await session.send_tool_response(
                                    function_responses=[types.FunctionResponse(
                                        id=fn.id,
                                        name=fn.name,
                                        response={"result": json.dumps(result)}
                                    )]
                                )
            finally:
                output_stream.close()
        
        # Run mic input and audio output concurrently
        await asyncio.gather(send_audio(), receive_and_play())

if __name__ == "__main__":
    print("🛡️  Guardian Agent starting...")
    print("🎧  Use headphones to prevent echo!\n")
    asyncio.run(run_guardian())