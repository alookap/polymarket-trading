from sortedcontainers import SortedDict
from typing import Optional, List, Tuple
from custom_types import PriceLevel
from decimal import Decimal

class OrderBook:
    """纯粹的订单簿实现，只负责维护价格和数量"""
    def __init__(self, market_id, yes_token_id, no_token_id):
        self.market_id = market_id
        self.yes_token_id = yes_token_id
        self.no_token_id = no_token_id

        self.bids = SortedDict()  # 买盘 price -> size
        self.asks = SortedDict()  # 卖盘 price -> size

        self.yes_position = Decimal("0")
        self.no_position = Decimal("0")

    def update_book(self, bids: List, asks: List): # 0.3s
        """完整更新订单簿"""
        self.bids.clear()
        self.asks.clear()

        for level in bids:
            price = Decimal(level['price'])
            size = Decimal(level['size'])
            self.bids[price] = size

        for level in asks:
            price = Decimal(level['price'])
            size = Decimal(level['size'])
            self.asks[price] = size

    def handle_price_change(self, changes: List[dict]): # 0.1s
        """处理单个价格变化"""
        for change in changes:
            price = Decimal(change['price'])
            size = Decimal(change['size'])
            side = change['side']

            if side == 'BUY':
                if size == 0:
                    self.bids.pop(price, None)
                else:
                    self.bids[price] = size
            else:  # SELL
                if size == 0:
                    self.asks.pop(price, None)
                else:
                    self.asks[price] = size

    def get_mid_price(self) -> Optional[Decimal]:  
        """获取中间价格"""
        if not self.bids or not self.asks:
            return None
        return (self.bids.peekitem(-1)[0] + self.asks.peekitem(0)[0]) / 2

    def get_best_bid_ask(self) -> Tuple[Optional[PriceLevel], Optional[PriceLevel]]:
        """获取最优买卖价"""
        best_bid = PriceLevel(self.bids.peekitem(-1)[0], self.bids.peekitem(-1)[1]) if self.bids else None
        best_ask = PriceLevel(self.asks.peekitem(0)[0], self.asks.peekitem(0)[1]) if self.asks else None
        return best_bid, best_ask

    def get_price_levels(self, depth: int) -> Tuple[List[PriceLevel], List[PriceLevel]]: # 0.x
        """获取指定深度的价格水平"""
        bids = [PriceLevel(p, s) for p, s in list(self.bids.items())[-depth:]]
        asks = [PriceLevel(p, s) for p, s in list(self.asks.items())[:depth]]
        return bids, asks
    
    def get_yes_position(self) -> Decimal:
        return self.yes_position
    
    def get_no_position(self) -> Decimal:
        return self.no_position
    
    def get_total_position(self) -> Decimal:
        """Calculate the total position as yes token position minus no token position"""
        return self.yes_position - self.no_position
    
    # 不是每一次price_change都需要重新更新，可以track一个上限和下限?
    