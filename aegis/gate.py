import logging
import json
import datetime
import aiohttp
import asyncio
import uuid
from typing import Dict, Any
from .classifier import classify_action
from .auth import request_touch_id
from .executor import search_and_execute
from .context import AegisContext
from . import config
from . import ws_server

logger = logging.getLogger("aegis.gate")
audit_logger = logging.getLogger("aegis_audit")



async def post_to_backend(endpoint: str, data: dict, await_response: bool = False):
    """
    Posts data to the backend. 
    By default, it's fire-and-forget (spawned as a background task).
    Set await_response=True to block until the request completes.
    """
    async def _post():
        try:
            headers = {"X-User-ID": config.USER_ID}
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(f"{config.BACKEND_URL}{endpoint}", json=data, timeout=5) as resp:
                    if resp.status != 200:
                        logger.warning(f"Backend returned {resp.status} for {endpoint}")
                    return resp.status == 200
        except Exception as e:
            logger.warning(f"Could not reach backend at {config.BACKEND_URL}: {e}")
            return False

    if await_response:
        return await _post()
    else:
        asyncio.create_task(_post())
        return True

async def request_remote_auth(proposed_action: str, classification: dict) -> bool:
    """
    Requests remote auth from backend and polls for result.
    Fallbacks to local Touch ID on timeout or error.
    """
    try:
        headers = {"X-User-ID": config.USER_ID}
        async with aiohttp.ClientSession(headers=headers) as session:
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
            logger.info('posting: %s', auth_data)
            async with session.post(f"{config.BACKEND_URL}/auth/request", json=auth_data, timeout=5) as resp:
                if resp.status != 200:
                    logger.warning("status: %s", resp.status)
                    logger.warning("body: %s", await resp.text())
                    return await request_touch_id(f"Aegis: {classification['speak']}")

                res_json = await resp.json()
                request_id = res_json.get("request_id")

            # 2. Broadcast to UI now that we have the real backend ID
            ws_server.broadcast("red_auth_started", data={
                "id": request_id,
                "request_id": request_id,
                "speak": classification.get("speak", "Aegis requires authentication"),
                "action": proposed_action,
                "reason": classification.get("reason", ""),
                "tool": classification.get("tool") or "unknown",
                "toolkit": classification.get("tool").split("_")[0].lower() if classification.get("tool") else "unknown"
            })

            # 3. Poll for Status
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
            return await request_touch_id(f"Aegis: {classification['speak']}")

    except Exception as e:
        logger.error(f"Error in remote auth flow: {e}, falling back to local")
        return await request_touch_id(f"Aegis: {classification['speak']}")

async def gate_action(proposed_action: str, context: AegisContext, pre_confirmed: bool = False, on_auth_request=None) -> Dict[str, Any]:
    start_time = datetime.datetime.now()
    logger.info(f"🤖 Processing proposed action: {proposed_action}")

    classification = await classify_action(proposed_action)

    tier = classification["tier"]
    speak = classification["speak"]
    tool = classification.get("tool")
    arguments = classification.get("arguments", {})

    logger.info(f"🎯 Tier: {tier} | Reason: {classification['reason']} | Pre-confirmed: {pre_confirmed}")
    logger.debug(f"🔧 Tool: {tool} | Args: {arguments}")

    result = {
        "action": proposed_action,
        "tier": tier,
        "reason": classification["reason"],
        "upgraded": classification["upgraded"],
        "speak": speak,
        "tool": tool,
        "executed": False,
        "auth_used": False,
        "confirmed_verbally": pre_confirmed,
        "blocked": False,
        "success": False,
        "error": None
    }

    try:
        if tier == "RED":
            logger.info("🔴 RED — requesting Auth...")
            # Notify caller (e.g. menu bar) that auth is happening
            if on_auth_request:
                try:
                    on_auth_request()
                except Exception:
                    pass
            
            # Try remote auth first, falls back to local Touch ID automatically
            # Broadcast is now handled inside request_remote_auth after it gets the ID
            authed = await request_remote_auth(proposed_action, classification)

            if not authed:
                logger.warning("🚫 Authentication failed or cancelled.")
                result["blocked"] = True
                result["error"] = "Authentication failed"
                ws_server.broadcast("red_auth_result", data={"approved": False})
            else:
                result["auth_used"] = True
                logger.info("✅ Authenticated")
                ws_server.broadcast("red_auth_result", data={"approved": True})

        elif tier == "YELLOW":
            if not pre_confirmed:
                # Don't block — return to voice layer to handle conversationally
                logger.info("� YELLOW — returning to voice for confirmation")
                result["needs_confirmation"] = True
                
                # Broadcast YELLOW confirm request
                ws_server.broadcast("yellow_confirm", data={
                    "id": str(uuid.uuid4()),
                    "speak": speak,
                    "question": speak,
                    "action": proposed_action,
                    "tool": tool or "unknown",
                    "toolkit": tool.split("_")[0].lower() if tool else "unknown"
                })
                return result
            else:
                # User already confirmed verbally via Gemini
                logger.info("🟡 YELLOW — pre-confirmed, executing")

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
        "output": result.get("output"),
        "error": result["error"],
        "duration_ms": duration_ms,
        "device": config.DEVICE_ID
    }
    audit_logger.info(json.dumps(audit_entry))

    # Post to Backend
    await post_to_backend("/action", audit_entry)

    # Broadcast Action Card to WebSocket (truncate output for performance)
    ws_data = {
        "id": str(uuid.uuid4()),
        "timestamp": audit_entry["timestamp"],
        "action": proposed_action,
        "tier": tier,
        "tool": tool or "unknown",
        "toolkit": tool.split("_")[0].lower() if tool else "unknown",
        "reason": classification["reason"],
        "upgraded": classification["upgraded"],
        "speak": speak,
        "auth_used": result["auth_used"],
        "blocked": result["blocked"],
        "success": result["success"],
        "duration_ms": duration_ms
    }

    if result.get("output"):
        out_str = str(result["output"])
        ws_data["output"] = out_str[:1000] + ("..." if len(out_str) > 1000 else "")

    if result.get("error"):
        ws_data["error"] = result["error"]

    ws_server.broadcast("action", data=ws_data)

    return result
