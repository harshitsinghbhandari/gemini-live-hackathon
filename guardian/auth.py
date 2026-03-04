import asyncio
import logging
import threading
from . import config

logger = logging.getLogger("guardian.auth")

try:
    import objc
    from LocalAuthentication import LAContext, LAPolicyDeviceOwnerAuthenticationWithBiometrics
except ImportError:
    logger.warning("LocalAuthentication not available. Touch ID will not work.")
    objc = None

async def request_touch_id(reason: str, timeout: int = None) -> bool:
    """
    Triggers Touch ID / Face ID on Mac.
    Returns True if authenticated, False if failed/cancelled.
    """
    if objc is None:
        logger.error("Touch ID requested but LocalAuthentication is not available.")
        return False

    if timeout is None:
        timeout = config.TOUCH_ID_TIMEOUT

    def _authenticate():
        try:
            context = LAContext.new()
            error = objc.nil

            can_auth, error = context.canEvaluatePolicy_error_(
                LAPolicyDeviceOwnerAuthenticationWithBiometrics,
                None
            )

            if not can_auth:
                logger.warning(f"Biometrics not available on this device: {error}")
                return False

            # Threading event to wait for async callback
            result_event = threading.Event()
            result_container = [False]

            def reply(success, error):
                if not success:
                    logger.warning(f"Touch ID failed or cancelled: {error}")
                result_container[0] = success
                result_event.set()

            context.evaluatePolicy_localizedReason_reply_(
                LAPolicyDeviceOwnerAuthenticationWithBiometrics,
                reason,
                reply
            )

            # Wait for event or timeout
            if not result_event.wait(timeout=timeout):
                logger.warning(f"Touch ID timed out after {timeout} seconds.")
                return False

            return result_container[0]
        except Exception as e:
            logger.error(f"Unexpected error during Touch ID authentication: {e}")
            return False

    return await asyncio.to_thread(_authenticate)
