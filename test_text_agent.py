import asyncio
import logging
from google import genai
from google.genai import types

from aegis.context import AegisContext
from aegis.voice import AegisVoiceAgent
from aegis import config

logger = logging.getLogger("aegis.text_test")

class TextAegisAgent(AegisVoiceAgent):
    async def _send_audio_loop(self, session, mic_info):
        """Overrides mic capture to read from stdin"""
        print("\n\n=== TEXT MODE TEST RUNNER ===")
        print("Type your commands below. The model will respond via text and audio.")
        print("Type 'quit' or 'exit' to stop.\n")
        
        while True:
            if self.context.is_executing_tool:
                await asyncio.sleep(0.5)
                continue
            
            # Use run_in_executor to avoid blocking the event loop with input()
            try:
                user_input = await asyncio.to_thread(input, "\nUser: ")
            except EOFError:
                break
            
            if user_input.strip() == "":
                continue
                
            if user_input.strip().lower() in ["exit", "quit", "q"]:
                print("Exiting...")
                if self.context.session:
                    await self.context.session.close()
                break

            print(f"Sending text: {user_input}")
            # In live API, we can send text directly
            await session.send_client_content(
                turns=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=user_input)]
                    )
                ],
                turn_complete=True
            )

async def main():
    # Setup basic logging to see model text
    logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
    
    from aegis.config import USER_ID, COMPOSIO_API_KEY
    from composio import Composio

    composio_client = None
    try:
        composio_client = Composio(api_key=COMPOSIO_API_KEY)
        print("✅ Composio initialized")
    except Exception as e:
        print(f"Warning: Composio failed to init: {e}")

    context = AegisContext(user_id=USER_ID, composio=composio_client)
    agent = TextAegisAgent(context)
    
    print("🌐 Connecting to Gemini Live API...")
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nForce quit.")
