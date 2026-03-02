import asyncio
import objc
from LocalAuthentication import LAContext, LAPolicyDeviceOwnerAuthenticationWithBiometrics

async def request_touch_id(reason: str) -> bool:
    """
    Triggers Touch ID / Face ID on Mac.
    Returns True if authenticated, False if failed/cancelled.
    """
    
    def _authenticate():
        context = LAContext.new()
        error = objc.nil
        
        can_auth, error = context.canEvaluatePolicy_error_(
            LAPolicyDeviceOwnerAuthenticationWithBiometrics,
            None
        )
        
        if not can_auth:
            print("❌ Biometrics not available on this device")
            return False
        
        # Threading event to wait for async callback
        import threading
        result_event = threading.Event()
        result_container = [False]
        
        def reply(success, error):
            result_container[0] = success
            result_event.set()
        
        context.evaluatePolicy_localizedReason_reply_(
            LAPolicyDeviceOwnerAuthenticationWithBiometrics,
            reason,
            reply
        )
        
        result_event.wait(timeout=30)  # 30 sec timeout
        return result_container[0]
    
    return await asyncio.to_thread(_authenticate)