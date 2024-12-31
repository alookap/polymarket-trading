import asyncio
import json
import logging
import websockets
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class WebsocketManager:
    """Manages WebSocket connections for both market and user data channels"""
    
    def __init__(
        self,
        market_url: str,
        user_url: str,
        api_key: str,
        api_secret: str,
        api_passphrase: str,
        condition_id: str,
        yes_id: str,
        no_id: str
    ):
        # URLs and authentication
        self.market_url = market_url
        self.user_url = user_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        
        # Market IDs
        self.condition_id = condition_id
        self.yes_id = yes_id
        self.no_id = no_id
        
        # WebSocket connections
        self.market_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.user_ws: Optional[websockets.WebSocketClientProtocol] = None
        
        # State management
        self.running = False
        self.market_handlers: List = []
        self.user_handlers: List = []

    def _get_market_subscribe_message(self) -> Dict[str, Any]:
        """Creates the market subscription message"""
        return {
            "assets_ids": [self.yes_id, self.no_id],
            "type": "market"
        }

    def _get_user_subscribe_message(self) -> Dict[str, Any]:
        """Creates the user subscription message with authentication"""
        return {
            "auth": {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "passphrase": self.api_passphrase
            },
            "markets": [self.condition_id],
            "type": "user"
        }

    async def start(self):
        """Starts both WebSocket connections concurrently"""
        self.running = True
        await asyncio.gather(
            self._connect_market(),
            self._connect_user()
        )

    async def stop(self):
        """Stops all WebSocket connections"""
        self.running = False
        if self.market_ws:
            await self.market_ws.close()
        if self.user_ws:
            await self.user_ws.close()

    async def _connect_market(self):
        """Connects to market data WebSocket and maintains the connection"""
        while self.running:
            try:
                async with websockets.connect(self.market_url) as ws:
                    self.market_ws = ws
                    logger.info("Connected to market websocket")
                    
                    # Send subscription message
                    subscribe_msg = self._get_market_subscribe_message()
                    await ws.send(json.dumps(subscribe_msg))
                    # logger.info(f"Sent market subscription: {subscribe_msg}")
                    print(f"Sent market subscription: {subscribe_msg}")
                    
                    await self._handle_market_messages()
            except Exception as e:
                logger.error(f"Market websocket error: {str(e)}")
                await asyncio.sleep(5)  # Reconnection delay

    async def _connect_user(self):
        """Connects to user data WebSocket and maintains the connection"""
        while self.running:
            try:
                async with websockets.connect(self.user_url) as ws:
                    self.user_ws = ws
                    logger.info("Connected to user websocket")
                    
                    # Send subscription message
                    subscribe_msg = self._get_user_subscribe_message()
                    await ws.send(json.dumps(subscribe_msg))
                    # logger.info(f"Sent user subscription: {subscribe_msg}")
                    print(f"Sent user subscription: {subscribe_msg}")

                    await self._handle_user_messages()
            except Exception as e:
                logger.error(f"User websocket error: {str(e)}")
                await asyncio.sleep(5)  # Reconnection delay

    async def _handle_market_messages(self):
        """Handles incoming market data messages"""
        while self.running and self.market_ws:
            try:
                message = await self.market_ws.recv()
                data = json.loads(message)
                
                # Check for price change events
                if data and isinstance(data, list): # and data[0].get('event_type') == "price_change":
                    logger.info(f"Received market price change: {data}")
                    for handler in self.market_handlers:
                        await handler(data)
            except Exception as e:
                logger.error(f"Error handling market message: {str(e)}")
                break

    async def _handle_user_messages(self):
        """Handles incoming user data messages"""
        while self.running and self.user_ws:
            try:
                message = await self.user_ws.recv()
                data = json.loads(message)
                logger.info(f"Received user message: {data}")
                for handler in self.user_handlers:
                    await handler(data)
            except Exception as e:
                logger.error(f"Error handling user message: {str(e)}")
                break

    def add_market_handler(self, handler):
        """Adds a new market data handler"""
        self.market_handlers.append(handler)

    def add_user_handler(self, handler):
        """Adds a new user data handler"""
        self.user_handlers.append(handler)