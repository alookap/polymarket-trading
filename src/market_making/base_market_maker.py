# market_making/base_market_maker.py
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional
from .custom_types import OrderRequest
from .orderbook import OrderBook

class BaseMarketMaker(ABC):
    """Base class for all market making strategies"""
    def __init__(self, orderbook: OrderBook, market_id: str, yes_asset_id: str, no_asset_id):
        self.orderbook = orderbook
        self.market_id = market_id
        self.yes_asset_id = yes_asset_id
        self.no_asset_id = no_asset_id
        self.position: Decimal = Decimal('0')

    @abstractmethod
    def calculate_fair_price(self) -> Optional[Decimal]:
        """Calculate the fair price based on market data"""
        pass

    @abstractmethod
    def generate_orders(self) -> List[OrderRequest]:
        """Generate orders based on the strategy"""
        pass

    def update_position(self, new_position: Decimal):
        """Update the current position"""
        self.position = new_position