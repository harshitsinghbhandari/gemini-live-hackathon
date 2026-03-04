import asyncio
import os
import sys
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

async def test_live():
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        tools=[{
            "function_declarations": [{
                "name": "execute_action",
                "description": "Execute an action",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING"},
                        "confirmed": {"type": "BOOLEAN"}
                    },
                    "required": ["action"]
                }
            }]
        }]
    )
    print("Connecting...")
    try:
        async with client.aio.live.connect(model="gemini-2.5-flash-native-audio-latest", config=config) as session:
            print("Connected! Sending ping...")
            await session.send_client_content(
                turns=[{"role": "user", "parts": [{"text": "Hello"}]}],
                turn_complete=True
            )
            print("Listening for response...")
            async for response in session.receive():
                print(f"Got response: {response}")
                break
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_live())
