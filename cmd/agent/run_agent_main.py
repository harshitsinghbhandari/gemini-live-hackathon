import asyncio
import logging
import argparse
from aegis.config import setup_logging, USER_ID
from aegis.context import AegisContext
from aegis.voice import AegisVoiceAgent

def main():
    parser = argparse.ArgumentParser(description="Aegis Voice Agent")
    parser.add_argument("--text-only", action="store_true", help="Disable audio loop for text-only testing")
    args = parser.parse_args()

    # Setup structured logging
    setup_logging()
    logger = logging.getLogger("aegis.main")

    logger.info("🛡️  Aegis starting...")
    if not args.text_only:
        logger.info("🎧  Use headphones to prevent echo!")
    else:
        logger.info("ℹ️  Running in TEXT-ONLY mode (mic disabled)")

    # Initialize context and agent
    context = AegisContext(user_id=USER_ID)
    agent = AegisVoiceAgent(context, text_only_mode=args.text_only)

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Aegis stopped by user.")
    except Exception as e:
        logger.exception(f"Aegis encountered a fatal error: {e}")

if __name__ == "__main__":
    main()
