import asyncio
import logging
from aegis.config import setup_logging, USER_ID
from aegis.context import AegisContext
from aegis.voice import AegisVoiceAgent

def main():
    # Setup structured logging
    setup_logging()
    logger = logging.getLogger("aegis.main")

    logger.info("🛡️  Aegis starting...")
    logger.info("🎧  Use headphones to prevent echo!")

    # Initialize context and agent
    context = AegisContext(user_id=USER_ID)
    agent = AegisVoiceAgent(context)

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Aegis stopped by user.")
    except Exception as e:
        logger.exception(f"Aegis encountered a fatal error: {e}")

if __name__ == "__main__":
    main()
