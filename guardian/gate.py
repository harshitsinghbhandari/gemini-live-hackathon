import logging
import json
import datetime
import aiohttp
import asyncio
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

async def post_to_backend(endpoint: str, data: dict):
    """Fire and forget — don't block the agent"""
    async def _post():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{config.BACKEND_URL}{endpoint}", json=data, timeout=5) as resp:
                    if resp.status != 200:
                        logger.warning(f"Backend returned {resp.status} for {endpoint}")
        except Exception as e:
            logger.warning(f"Could not reach backend at {config.BACKEND_URL}: {e}")

    asyncio.create_task(_post())

async def request_remote_auth(proposed_action: str, classification: dict) -> bool:
    """
    Requests remote auth from backend and polls for result.
    Fallbacks to local Touch ID on timeout or error.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Request Auth
            auth_data = {
                "action": proposed_action,
                "tier": classification["tier"],
                "reason": classification["reason"],
                "speak": classification["speak"],
                "tool": classification.get("tool", ""),
                "arguments": classification.get("arguments", {}),
                "device": config.DEVICE_ID
            }
            async with session.post(f"{config.BACKEND_URL}/auth/request", json=auth_data, timeout=5) as resp:
                if resp.status != 200:
                    logger.warning("Backend auth request failed, falling back to local")
                    return await request_touch_id(f"Guardian: {classification['speak']}")

                res_json = await resp.json()
                request_id = res_json.get("request_id")

            # 2. Poll for Status
            start_poll = datetime.datetime.now()
            while (datetime.datetime.now() - start_poll).total_seconds() < 30:
                async with session.get(f"{config.BACKEND_URL}/auth/status/{request_id}", timeout=5) as resp:
                    if resp.status == 200:
                        status_data = await resp.json()
                        status = status_data.get("status")
                        if status == "approved":
                            return True
                        if status == "denied":
                            return False

                await asyncio.sleep(2)

            logger.warning("Remote auth timed out, falling back to local")
            return await request_touch_id(f"Guardian: {classification['speak']}")

    except Exception as e:
        logger.error(f"Error in remote auth flow: {e}, falling back to local")
        return await request_touch_id(f"Guardian: {classification['speak']}")

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
            logger.info("🔴 RED — requesting Auth...")
            # Try remote auth first, falls back to local Touch ID automatically
            authed = await request_remote_auth(proposed_action, classification)

            if not authed:
                logger.warning("🚫 Authentication failed or cancelled.")
                result["blocked"] = True
                result["error"] = "Authentication failed"
            else:
                result["auth_used"] = True
                logger.info("✅ Authenticated")

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
        "duration_ms": duration_ms,
        "device": config.DEVICE_ID
    }
    audit_logger.info(json.dumps(audit_entry))

    # Post to Backend
    await post_to_backend("/action", audit_entry)

    return result
