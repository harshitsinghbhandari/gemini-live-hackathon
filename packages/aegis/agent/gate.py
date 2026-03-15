import os
import logging
import json
import datetime
import aiohttp
import asyncio
import uuid
from typing import Dict, Any
from aegis.agent.classifier import classify_action
from aegis.auth import request_touch_id
from aegis.runtime.screen_executor import execute_screen_action
from aegis.tools.declarations import get_screen_tool_declarations
from aegis.runtime.context import AegisContext
from configs.agent import config
from aegis.interfaces import ws_server

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.formatTime(record),
        })

handler = logging.StreamHandler()
if os.getenv("LOG_FORMAT", "text") == "json":
    handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])

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
    Includes a visual screenshot crop for the mobile app to display.
    Fallbacks to local Touch ID on timeout or error.
    """
    try:
        # Capture visual context for the auth request
        visual_context = {}
        try:
            from aegis.perception.screen.capture import capture_screen
            shot = capture_screen(quality=50, scale_to=(800, 520))
            visual_context = {
                "base64_image": shot["base64"],
                "mime_type": shot["mime_type"],
                "action_description": proposed_action,
                "element_label": classification.get("tool", "system_action")
            }
            logger.info("Visual context captured for auth request.")
        except Exception as vc_err:
            logger.warning(f"Could not capture visual context: {vc_err}")

        headers = {"X-User-ID": config.USER_ID}
        async with aiohttp.ClientSession(headers=headers) as session:
            # 1. Request Auth with visual context
            auth_data = {
                "action": proposed_action,
                "tier": classification.get("tier", "RED"),
                "reason": classification.get("reason", "Aegis requires authentication"),
                "speak": classification.get("speak", "Aegis requires authentication for this action."),
                "tool": classification.get("tool", ""),
                "arguments": classification.get("arguments", {}),
                "device": config.DEVICE_ID,
                "visual_context": visual_context
            }
            logger.info('posting: %s', auth_data)
            async with session.post(f"{config.BACKEND_URL}/auth/request", json=auth_data, timeout=5) as resp:
                if resp.status != 200:
                    logger.warning("status: %s", resp.status)
                    logger.warning("body: %s", await resp.text())
                    return await request_touch_id(f"Aegis: {classification.get('speak', 'Authentication required')}")

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
            return await request_touch_id(f"Aegis: {classification.get('speak', 'Authentication required')}")

    except Exception as e:
        logger.error(f"Error in remote auth flow: {e}, falling back to local")
        return await request_touch_id(f"Aegis: {classification.get('speak', 'Authentication required')}")

async def gate_action(proposed_action: str, context: AegisContext, pre_confirmed: bool = False, on_auth_request: callable = None, tool_name: str = None, tool_args: dict = None, call_id: str = None) -> Dict[str, Any]:
    """
    The secure gateway for all Aegis actions.
    Steps:
    1. Classify risk tier (GREEN, YELLOW, RED) - skip if tool_name is provided
    2. Check if this specific action was previously session-approved (GREEN or pre-authorized YELLOW)
    3. If RED, trigger Touch ID / Biometric auth
    4. If YELLOW, ask for verbal confirmation (handled by voice.py, but we signal here)
    5. Execute if auth is cleared
    """
    start_time = datetime.datetime.now()
    logger.info(f"🤖 Processing proposed action: {proposed_action}")

    try:
        # 1. Classify / Fetch existing classification
        if tool_name:
            # Skip full classification if tool is already known
            classification = await classify_action(proposed_action, tool_hint=tool_name)
            tool = tool_name
            arguments = tool_args or {}
        else:
            classification = await classify_action(proposed_action)
            tool = classification.get("tool")
            arguments = classification.get("arguments", {})

        tier = classification.get("tier", "RED")
        speak = classification.get("speak", "I need to check something before I do that.")

        logger.info(f"🎯 Tier: {tier} | Reason: {classification.get('reason')} | Pre-confirmed: {pre_confirmed}")
        logger.debug(f"🔧 Classification detailed: {json.dumps(classification)}")
        logger.debug(f"🔧 Tool: {tool} | Args: {arguments}")

        result = {
            "action": proposed_action,
            "tier": tier,
            "reason": classification.get("reason"),
            "upgraded": classification.get("upgraded"),
            "speak": speak,
            "tool": tool,
            "call_id": call_id,
            "executed": False,
            "auth_used": False,
            "confirmed_verbally": pre_confirmed,
            "blocked": False,
            "success": False,
            "error": None
        }

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
                # Return to voice layer to handle passively
                logger.info("🟡 YELLOW — requesting passive confirmation")
                result["needs_passive_confirmation"] = True
                
                # Broadcast YELLOW confirm request (for UI status indication)
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
                # User already confirmed verbally via Gemini context or listener
                logger.info("🟡 YELLOW — confirmed, executing")

        elif tier == "GREEN":
            logger.info("🟢 GREEN — proceeding with execution")

        # Execute via correct executor if not blocked
        if not result["blocked"] and tool:
            SCREEN_TOOL_NAMES = [t["name"] for t in get_screen_tool_declarations()]
            if tool in SCREEN_TOOL_NAMES:
                logger.info(f"🖥️  Native Screen Executor: {tool}")
                exec_result = await execute_screen_action(tool, arguments)
            else:
                logger.warning(f"⚠️  Unsupported tool requested: {tool}")
                exec_result = {"success": False, "error": f"Tool {tool} is not supported or disabled."}
            
            result["success"] = exec_result["success"]
            if exec_result["success"]:
                result["output"] = exec_result.get("data") or exec_result.get("description")
                result["executed"] = True
                # Pass through additional keys (like 'plan') from the executor
                for k, v in exec_result.items():
                    if k not in result:
                        result[k] = v
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
        "id": call_id or str(uuid.uuid4()),
        "timestamp": audit_entry["timestamp"],
        "action": proposed_action,
        "tier": tier,
        "tool": tool or "unknown",
        "toolkit": tool.split("_")[0].lower() if tool else "unknown",
        "reason": classification.get("reason", ""),
        "upgraded": classification.get("upgraded", False),
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
