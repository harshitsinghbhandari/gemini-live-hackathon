import logging
import json
import datetime
from typing import Dict, Any
from .classifier import classify_action
from .auth import request_touch_id
from .executor import search_and_execute
from .context import GuardianContext
from . import config

logger = logging.getLogger("guardian.gate")
audit_logger = logging.getLogger("guardian_audit")

async def request_yellow_confirmation(speak: str, context: GuardianContext) -> bool:
    """
    Guardian speaks the confirmation request and listens for yes/no.
    Returns True if user confirms, False if denied.
    """
    if not context.session:
        logger.warning("No live session — defaulting to blocked")
        return False

    try:
        # Send confirmation request as text to Gemini
        await context.session.send_client_content(
            turns=[{
                "role": "user",
                "parts": [{
                    "text": f"""
                    YELLOW tier action detected.
                    Say exactly this to the user: "{speak}. Should I proceed?"
                    Then listen for their yes or no response.
                    If they say yes or confirm → respond with exactly: CONFIRMED
                    If they say no or cancel → respond with exactly: CANCELLED
                    """
                }]
            }],
            turn_complete=True
        )

        # Listen for Gemini's classification of the user's response
        async for response in context.session.receive():
            if response.server_content and response.server_content.model_turn:
                for part in response.server_content.model_turn.parts:
                    if hasattr(part, 'text') and part.text:
                        text = part.text.strip().upper()
                        logger.info(f"🟡 Confirmation response: {text}")
                        if "CONFIRMED" in text:
                            return True
                        if "CANCELLED" in text:
                            return False

            if response.server_content and response.server_content.turn_complete:
                break
    except Exception as e:
        logger.error(f"Error during verbal confirmation: {e}")

    return False  # default to safe

async def gate_action(proposed_action: str, context: GuardianContext) -> Dict[str, Any]:
    start_time = datetime.datetime.now()
    logger.info(f"🤖 Processing proposed action: {proposed_action}")

    classification = await classify_action(proposed_action)

    tier = classification["tier"]
    speak = classification["speak"]
    tool = classification.get("tool")
    arguments = classification.get("arguments", {})

    logger.info(f"🎯 Tier: {tier} | Reason: {classification['reason']}")
    logger.debug(f"🔧 Tool: {tool} | Args: {arguments}")

    result = {
        "action": proposed_action,
        "tier": tier,
        "reason": classification["reason"],
        "upgraded": classification["upgraded"],
        "tool": tool,
        "executed": False,
        "auth_used": False,
        "confirmed_verbally": False,
        "blocked": False,
        "success": False,
        "error": None
    }

    try:
        if tier == "RED":
            logger.info("🔴 RED — requesting Touch ID...")
            authed = await request_touch_id(f"Guardian: {speak}")
            if not authed:
                logger.warning("🚫 Touch ID authentication failed or cancelled.")
                result["blocked"] = True
                result["error"] = "Touch ID authentication failed"
            else:
                result["auth_used"] = True
                logger.info("✅ Authenticated via Touch ID")

        elif tier == "YELLOW":
            logger.info("🟡 YELLOW — requesting verbal confirmation...")
            confirmed = await request_yellow_confirmation(speak, context)
            if not confirmed:
                logger.warning("🚫 User declined verbal confirmation.")
                result["blocked"] = True
                result["error"] = "Verbal confirmation declined"
            else:
                result["confirmed_verbally"] = True
                logger.info("✅ User confirmed verbally")

        elif tier == "GREEN":
            logger.info("🟢 GREEN — proceeding with execution")

        # Execute via Composio if not blocked
        if not result["blocked"] and tool:
            exec_result = await search_and_execute(proposed_action, arguments, context)
            result["success"] = exec_result["success"]
            if exec_result["success"]:
                result["output"] = exec_result.get("data")
                result["executed"] = True
            else:
                result["error"] = exec_result.get("error")
                logger.error(f"Execution error: {result['error']}")

    except Exception as e:
        logger.exception(f"Unexpected error in gate_action: {e}")
        result["error"] = str(e)
        result["blocked"] = True

    duration_ms = int((datetime.datetime.now() - start_time).total_seconds() * 1000)

    # Audit Trail Logging
    audit_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "action": proposed_action,
        "tier": tier,
        "tool": tool,
        "arguments": arguments,
        "auth_used": result["auth_used"],
        "confirmed_verbally": result["confirmed_verbally"],
        "blocked": result["blocked"],
        "success": result["success"],
        "error": result["error"],
        "duration_ms": duration_ms
    }
    audit_logger.info(json.dumps(audit_entry))

    return result
