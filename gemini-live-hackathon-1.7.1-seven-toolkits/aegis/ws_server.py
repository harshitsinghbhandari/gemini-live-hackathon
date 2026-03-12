import asyncio
import json
import logging
import websockets
from typing import Set

logger = logging.getLogger("aegis.ws_server")

class AegisWSServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.server = None
        self.max_connections = 5
        self.on_yellow_response = None  # Future expansion: handle app responses
        self.stop_event = asyncio.Event()

    async def handler(self, websocket):
        if len(self.clients) >= self.max_connections:
            logger.warning(f"Connection rejected from {websocket.remote_address}: Max clients reached.")
            await websocket.close(code=1008, reason="Max connections reached")
            return

        self.clients.add(websocket)
        logger.info(f"✅ UI Client connected from {websocket.remote_address}. Total: {len(self.clients)}")
        
        try:
            async for message in websocket:
                # Listener for future client-to-agent events
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            logger.info(f"❌ UI Client disconnected. Total: {len(self.clients)}")

    async def broadcast(self, message_dict: dict):
        if not self.clients:
            return

        message = json.dumps(message_dict)
        # Use asyncio.gather to send to all clients concurrently
        # return_exceptions=True ensures one dead client doesn't stop others
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )

    async def start(self):
        """Runs the server. Should be called as a background task."""
        try:
            async with websockets.serve(self.handler, self.host, self.port):
                logger.info(f"📡 WebSocket server running on ws://{self.host}:{self.port}")
                await self.stop_event.wait()
            logger.info("📡 WebSocket server stopped.")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"⚠️ WebSocket server error: {e}")

    def stop(self):
        """Triggers the server to stop."""
        self.stop_event.set()


# Singleton management
_server_instance = AegisWSServer()

def get_server():
    return _server_instance

def broadcast(event: str, value=None, data=None):
    """
    Fire-and-forget broadcast helper. 
    Safe to call from any async context.
    """
    msg = {"event": event}
    if value is not None:
        msg["value"] = value
    if data is not None:
        msg["data"] = data

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_server_instance.broadcast(msg))
    except RuntimeError:
        # No running loop, just ignore. This keeps the agent from crashing.
        pass
    except Exception as e:
        logger.error(f"Failed to schedule broadcast: {e}")
