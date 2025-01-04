from typing import Dict, List, Optional, Union
import asyncio
from concurrent.futures import ThreadPoolExecutor
from py_clob_client.clob_types import OrderArgs, OrderType
from decimal import Decimal
import logging
from dataclasses import dataclass
from .custom_types import Order, OrderRequest

@dataclass
class OrderResponse:
    order_id: str
    status: str
    timestamp: int
    filled_size: Decimal = Decimal('0')
    remaining_size: Decimal = Decimal('0')
    price: Optional[Decimal] = None

class OrderManager:
    """Manage the Order Lifecycle"""
    def __init__(self, api_client):
        self.api_client = api_client
        self.active_orders: Dict[str, Order] = {}  # order_id -> Order
        self.market_orders: Dict[str, List[str]] = {}  # yes_token_id -> price -> [order_id]
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=5)  # 创建线程池

    async def _run_in_executor(self, func, *args, **kwargs):
        """在线程池中异步运行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)

    async def place_order(self, request: OrderRequest) -> str:
        """
        提交订单并返回 order_id
        """
        try:
            gtc_order_args = OrderArgs(
                price=request.price,
                size=request.size,
                side=request.side,
                token_id=request.asset_id,
            )
            signed_gtc_order = await self._run_in_executor(
                self.api_client.create_order,
                gtc_order_args
            )
            gtc_resp = await self._run_in_executor(
                self.api_client.post_order,
                signed_gtc_order,
                OrderType.GTC
            )

            if gtc_resp['success'] == True:
                if gtc_resp['status'] == 'live':
                    self._add_order(gtc_resp['orderID'], request)
                return gtc_resp['orderID'] ### Maybe we dont need to return anything
            else:
                self.logger.error(f"Failed to place order: {gtc_resp['errorMsg']}")
        
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            raise

    async def cancel_order(self, order_id_or_ids):
        """
        Cancel order(s).

        :param order_id_or_ids: A single order ID (str) or a list of order IDs (list of str).
        """
        try:
            if isinstance(order_id_or_ids, str):
                cancel_resp = await self._run_in_executor(self.api_client.cancel_order, order_id_or_ids)
                self._remove_order(cancel_resp['canceled'])
                ### If cancel successfully or not
            elif isinstance(order_id_or_ids, list):
                cancel_resp = await self._run_in_executor(self.api_client.cancel_orders, order_id_or_ids)
                self._remove_order(cancel_resp['canceled'])
                # self._remove_order(order_id_or_ids)
            else:
                raise ValueError("Input must be a str or a list of str.")
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order(s) {order_id_or_ids}: {e}")
            raise

    async def cancel_all_orders(self, market_id: str): # market_id ## not complete ## token id & market id
        """
        取消特定市场的所有订单
        """
        try:
            await self._run_in_executor(self.api_client.cancel_market_orders, market_id)
            ### cancel id from active_orders & market_orders
        except Exception as e:
            self.logger.error(f"Failed to cancel order at market: {e}")
            raise

    async def handle_order_update(self, response: OrderResponse): # 在order filled之后调用
        """
        处理订单状态更新
        """
        order_id = response.order_id
        status = response.status

        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            order.status = status

            if status in ['FILLED', 'CANCELED', 'REJECTED']: ### CANCELED & REJECTED 我可能本来就会count in, so double count in user channel
                self._remove_order(order_id)

    def _add_order(self, order_id: str, request: OrderRequest):
        """
        Add an order to tracking lists
        """
        order = Order(
            id=order_id,
            request=request, 
            status='ACTIVE',
            timestamp=int(asyncio.get_event_loop().time()) # 额外添加
        )
        self.active_orders[order_id] = order

        token_id = request.yes_asset_id
        if token_id not in self.market_orders:
            self.market_orders[token_id] = []
        self.market_orders[token_id].append(order_id) ### 有没有必要改成双层索引？可以marginal提速

    def _remove_order(self, order_ids: Union[str, List[str]]):
        """
        Remove one or more orders from tracking lists.
        """
        if isinstance(order_ids, str):
            order_ids = [order_ids]
        for order_id in order_ids:
            if order_id in self.active_orders:
                order = self.active_orders.pop(order_id)
                token_id = order.request.yes_asset_id
                if token_id in self.market_orders:
                    self.market_orders[token_id].remove(order_id)
                    # 最后一个元素remove掉需不需要删除？从实际场景考虑不删除更好
                    # remove followed by add func

    def get_active_orders(self, market_id: str) -> List[Order]: ### token_id 
        """
        Get active orders for a specific market
        """
        order_ids = self.market_orders.get(market_id, [])
        return [self.active_orders[oid] for oid in order_ids if oid in self.active_orders]
    

