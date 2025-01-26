### add check-and-hold logic
import logging
from decimal import Decimal
from typing import List, Optional, Tuple
from .base_market_maker import BaseMarketMaker
from .custom_types import OrderRequest, Order
from .orderbook import OrderBook
from .order_manager import OrderManager

class SimplestMM(BaseMarketMaker):
    def __init__(
        self,
        orderbook: OrderBook,
        market_id: str,  # condition id
        yes_asset_id: str,
        no_asset_id: str,
        order_manager: OrderManager,            # <--- 新增: 注入 order_manager
        width: Decimal = Decimal('0.01'),  # 20 bps spread
        price_threshold: Decimal = Decimal('0.001'),  # 10 bps threshold for updates
    ):
        super().__init__(orderbook, market_id, yes_asset_id, no_asset_id)

        self.order_manager = order_manager

        self.width = width
        self.price_threshold = price_threshold
        self.last_fair_price: Optional[Decimal] = None

        self.normal_size = Decimal('5')

        self.yes_position: Decimal = Decimal('0')
        self.no_position: Decimal = Decimal('0')
    
    def calculate_fair_price(self):
        pass
    
    def generate_orders(self) -> Tuple[List[str], List[OrderRequest]]:
        """
        在这里直接对比“当前活跃订单”和“我们想要的最佳挂单”。
        返回:
            orders_to_cancel: 需要撤销的订单ID列表
            orders_to_place: 需要新下的订单请求列表
        """
        # 1. 从OrderManager拿到当前活跃订单 (针对本market_id)
        current_orders: List[Order] = self.order_manager.get_active_orders(self.market_id)

        # 2. 先拿到市场最佳买卖价
        bid_ask = self.orderbook.get_best_bid_ask()
        bid1 = bid_ask[0].price
        ask1 = bid_ask[1].price

        # 这里可以随便定量
        ask_size = Decimal('5')
        bid_size = Decimal('5')

        self.yes_position = self.orderbook.yes_position
        self.no_position = self.orderbook.no_position

        # 目标：我们希望挂两个订单：
        #   1) 如果 yes_position > ask_size，就挂 sell on yes_token at ask1，否则挂 buy on no_token at 1-ask1
        #   2) 如果 no_position > bid_size，就挂 sell on no_token at (1-bid1)，否则挂 buy on yes_token at bid1

        # 3. 先用变量记录我们“想要”的2个目标OrderRequest

        desired_orders: List[OrderRequest] = []
        orders_to_cancel: List[str] = []

        ask_side_place = True
        bid_side_place = True

        for order in self.order_manager.get_active_orders(self.market_id, "SELL"):
            if order.yes_price == ask1:
                ask_side_place = False 
                logging.info(f"Keeping existing SELL order at {ask1}, order size: {order.remaining_size}")
            else:
                orders_to_cancel.append(order.id)
                logging.info(f"Canceling outdated SELL order at {order.yes_price}")
                
        for order in self.order_manager.get_active_orders(self.market_id, "BUY"):
            if order.yes_price == bid1:
                bid_side_place = False 
                logging.info(f"Keeping existing BUY order at {bid1}, order size: {order.remaining_size}")
            else:
                orders_to_cancel.append(order.id)
                logging.info(f"Canceling outdated BUY order at {order.yes_price}")
                    
        if ask_side_place:
            # (A) 对应 yes_token 的操作 (ask side / or buy no_token)
            if self.yes_position >= ask_size:
                # 卖YES
                desired_orders.append(OrderRequest(
                    side='SELL',
                    price=ask1,
                    size=ask_size,
                    size_at_level=self.orderbook.get_size_at_level('SELL', ask1),
                    market_id=self.market_id,
                    asset_id=self.yes_asset_id,
                    yes_asset_id=self.yes_asset_id,
                ))
            else:
                # 买NO
                desired_orders.append(OrderRequest(
                    side='BUY',
                    price=(Decimal('1') - ask1),
                    size=ask_size,
                    size_at_level=self.orderbook.get_size_at_level('SELL', ask1),
                    market_id=self.market_id,
                    asset_id=self.no_asset_id,
                    yes_asset_id=self.yes_asset_id,
                ))

        if bid_side_place:
            # (B) 对应 no_token 的操作 (sell side / or buy yes_token)
            if self.no_position >= bid_size:
                desired_orders.append(OrderRequest(
                    side='SELL',
                    price=(Decimal('1') - bid1),
                    size=bid_size,
                    size_at_level=self.orderbook.get_size_at_level('BUY', bid1),
                    market_id=self.market_id,
                    asset_id=self.no_asset_id,
                    yes_asset_id=self.yes_asset_id,
                ))
            else:
                desired_orders.append(OrderRequest(
                    side='BUY',
                    price=bid1,
                    size=bid_size,
                    size_at_level=self.orderbook.get_size_at_level('BUY', bid1),
                    market_id=self.market_id,
                    asset_id=self.yes_asset_id,
                    yes_asset_id=self.yes_asset_id,
                ))

        return orders_to_cancel, desired_orders


