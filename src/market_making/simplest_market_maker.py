from decimal import Decimal
import random
from typing import List, Optional
from .base_market_maker import BaseMarketMaker
from .custom_types import OrderRequest, PriceLevel
from .orderbook import OrderBook

class SimplestMM(BaseMarketMaker):
    def __init__(
        self,
        orderbook: OrderBook,
        market_id: str, # condition id
        yes_asset_id: str,
        no_asset_id: str,
        width: Decimal = Decimal('0.01'),  # 20 bps spread
        price_threshold: Decimal = Decimal('0.001'),  # 10 bps threshold for updates
    ):
        super().__init__(orderbook, market_id, yes_asset_id, no_asset_id)
        self.width = width
        self.price_threshold = price_threshold
        self.last_fair_price: Optional[Decimal] = None

        self.normal_size = Decimal('5')

        self.yes_position: Decimal = Decimal('0')
        self.no_position: Decimal = Decimal('0')
    
    def calculate_fair_price(self):
        pass
    
    def generate_orders(self):
        bid_ask = self.orderbook.get_best_bid_ask()
        bid1 = bid_ask[0].price
        ask1 = bid_ask[1].price
        orders = []

        ask_size = 5
        bid_size = 5

        self.yes_position = self.orderbook.yes_position
        self.no_position = self.orderbook.no_position
        # Determine positions and construct orders based on them

        if self.yes_position > ask_size:
            # Prefer placing orders on yes token
            orders.append(
                OrderRequest(
                    side='SELL',
                    price= ask1, # fair_price + half_width,
                    # size=self._generate_random_size(),
                    size = ask_size, 
                    size_at_level=self.orderbook.get_size_at_level('SELL', ask1),
                    market_id=self.market_id,
                    asset_id=self.yes_asset_id,
                    yes_asset_id=self.yes_asset_id,
                )
            )

        else:
            orders.append(
                OrderRequest(
                    side='BUY',
                    price= 1-ask1,
                    # size=self._generate_random_size(),
                    size = ask_size,
                    size_at_level=self.orderbook.get_size_at_level('SELL', ask1),
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
                    price=1-bid1,
                    size=bid_size,
                    size_at_level=self.orderbook.get_size_at_level('BUY', bid1),
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
                    price=bid1,
                    size=bid_size,
                    size_at_level=self.orderbook.get_size_at_level('BUY', bid1),
                    market_id=self.market_id,
                    asset_id=self.yes_asset_id,
                    yes_asset_id=self.yes_asset_id,
                )
            )

            
        return orders

    
    
    

