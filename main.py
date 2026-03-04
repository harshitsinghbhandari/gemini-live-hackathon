import asyncio
import logging
from guardian.config import setup_logging, USER_ID
from guardian.context import GuardianContext
from guardian.voice import GuardianVoiceAgent

def main():
    # Setup structured logging
    setup_logging()
    logger = logging.getLogger("guardian.main")

    logger.info("🛡️  Guardian Agent starting...")
    logger.info("🎧  Use headphones to prevent echo!")

    # Initialize context and agent
    context = GuardianContext(user_id=USER_ID)
    agent = GuardianVoiceAgent(context)

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Guardian Agent stopped by user.")
    except Exception as e:
        logger.exception(f"Guardian Agent encountered a fatal error: {e}")

if __name__ == "__main__":
    main()
