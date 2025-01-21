# market_making/simple_market_maker.py
from decimal import Decimal
import random
from typing import List, Optional
from .base_market_maker import BaseMarketMaker
from .custom_types import OrderRequest, PriceLevel
from .orderbook import OrderBook

class SimpleMarketMaker(BaseMarketMaker):
    """A simple market making strategy implementation"""
    def __init__(
        self,
        orderbook: OrderBook,
        market_id: str, # condition id
        yes_asset_id: str,
        no_asset_id: str,
        width: Decimal = Decimal('0.01'),  # 20 bps spread
        price_threshold: Decimal = Decimal('0.001'),  # 10 bps threshold for updates
        tick_size: Decimal = Decimal('0.001')
    ):
        super().__init__(orderbook, market_id, yes_asset_id, no_asset_id)
        self.width = width
        self.price_threshold = price_threshold
        self.last_fair_price: Optional[Decimal] = None

        self.normal_size = Decimal('5')
        self.tick_size = tick_size

        self.yes_position: Decimal = Decimal('0')
        self.no_position: Decimal = Decimal('0')

    def calculate_fair_price(self) -> Optional[Decimal]:
        """
        Calculate fair price as volume-weighted average price of top 10 levels
        """
        bids, asks = self.orderbook.get_price_levels(10)
        if not bids or not asks:
            return None

        total_bid_volume = Decimal('0')
        total_bid_value = Decimal('0')
        total_ask_volume = Decimal('0')
        total_ask_value = Decimal('0')

        # Process bid side
        for level in bids:
            total_bid_volume += level.size
            total_bid_value += level.price * level.size

        # Process ask side
        for level in asks:
            total_ask_volume += level.size
            total_ask_value += level.price * level.size

        # Calculate VWAP
        if total_bid_volume == 0 or total_ask_volume == 0:
            return None

        bid_vwap = total_bid_value / total_bid_volume
        ask_vwap = total_ask_value / total_ask_volume
        
        return (bid_vwap + ask_vwap) / 2

    def _should_update_orders(self, new_fair_price: Decimal) -> bool:
        """
        Determine if we should update orders based on price movement
        """
        if self.last_fair_price is None:
            return True
            
        price_change = abs(new_fair_price - self.last_fair_price) / self.last_fair_price
        return price_change > self.price_threshold

    def _generate_random_size(self) -> Decimal:
        """Generate a random order size between 5 and 10"""
        return Decimal(str(random.randint(5, 10)))

    def generate_orders(self) -> List[OrderRequest]:
        """
        Generate buy and sell orders around the fair price
        """
        fair_price = self.calculate_fair_price()
        if fair_price is None:
            return []

        if not self._should_update_orders(fair_price):
            return []

        self.last_fair_price = fair_price
        half_width = self.width / 2

        orders = []

        ask_size = 5
        bid_size = 5

        # Determine positions and construct orders based on them
        if self.yes_position > ask_size:
            # Prefer placing orders on yes token
            orders.append(
                OrderRequest(
                    side='SELL',
                    price=fair_price + half_width,
                    # size=self._generate_random_size(),
                    size = ask_size, 
                    size_at_level=self.orderbook.get_size_at_level('SELL', fair_price + half_width),
                    market_id=self.market_id,
                    asset_id=self.yes_asset_id,
                    yes_asset_id=self.yes_asset_id,
                )
            )

        else:
            orders.append(
                OrderRequest(
                    side='BUY',
                    price= (1-fair_price) - half_width,
                    # size=self._generate_random_size(),
                    size = ask_size,
                    size_at_level=self.orderbook.get_size_at_level('SELL', fair_price + half_width),
                    market_id=self.market_id,
                    asset_id=self.no_asset_id,
                    yes_asset_id=self.yes_asset_id,
                )
            )

        if self.no_position > bid_size:
            # sell order on no token
            orders.append(
                OrderRequest(
                    side='SELL',
                    price=(1-fair_price) + half_width,
                    size=bid_size,
                    size_at_level=self.orderbook.get_size_at_level('BUY', fair_price - half_width),
                    market_id=self.market_id,
                    asset_id=self.no_asset_id,
                    yes_asset_id=self.yes_asset_id,
                )
            )

        else:
            # BUY ORDER ON YES TOKEN
            orders.append(
                OrderRequest(
                    side='BUY',
                    price=fair_price - half_width,
                    size=bid_size,
                    size_at_level=self.orderbook.get_size_at_level('BUY', fair_price - half_width),
                    market_id=self.market_id,
                    asset_id=self.yes_asset_id,
                    yes_asset_id=self.yes_asset_id,
                )
            )

        return orders