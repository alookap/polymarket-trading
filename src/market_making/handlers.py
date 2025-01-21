from decimal import Decimal
import logging
from typing import Protocol

logger = logging.getLogger(__name__)

class MarketDataHandler:
    def __init__(self, order_book, config):
        self.order_book = order_book
        self.config = config
    
    async def __call__(self, data):
        """处理市场数据"""
        try:
            for item in data:
                if item.get('asset_id') == self.config.yes_id:
                    if item.get('event_type') == 'book':
                        self.order_book.update_book(
                            item.get('bids'),
                            item.get('asks')
                        )
                    elif item.get('event_type') == 'price_change':
                        self.order_book.handle_price_change(
                            item.get('changes')
                        )
        except Exception as e:
            logger.error(f"Error in market handler: {e}", exc_info=True)
            raise  # 让Runner处理异常



class UserDataHandler:
    def __init__(self, order_book, strategy, config):
        """
        :param order_book: 维护 yes_position / no_position 的对象
        :param strategy:    需要根据最新仓位更新策略的对象
        :param config:      存储一些必要的id或key，例如 yes_id, no_id, api_key 等
        """
        self.order_book = order_book
        self.strategy = strategy
        self.config = config
    
    async def __call__(self, data):
        """用户数据流处理入口"""
        try:
            for item in data:
                # 只处理已撮合(MATCHED)且资产在 yes/no 内的 trade 事件
                if (item.get('event_type') == 'trade'
                    and item.get('asset_id') in {self.config.yes_id, self.config.no_id}
                    and item.get('status') == 'MATCHED'):
                    
                    await self._handle_trade(item)
                    
                    # 每处理完一笔更新策略持仓
                    new_position = self.order_book.get_total_position()
                    # self.strategy.update_position(new_position)
                    
        except Exception as e:
            logger.error(f"Error in user handler: {e}", exc_info=True)
            raise  # 如果想在外部捕捉这里的异常，可以在 Runner 做异常处理
    
    async def _handle_trade(self, trade_data):
        """统一处理一笔 trade 数据"""
        taker_asset_id = trade_data.get('asset_id')
        side = trade_data.get('side')  # 'BUY' or 'SELL'
        
        # 先看是否我( self.config.api_key )是 maker
        for maker_order in trade_data.get('maker_orders', []):
            if maker_order.get('owner') == self.config.api_key:
                await self._handle_maker_trade(maker_order, taker_asset_id, side)
        
        # 再看是否我( self.config.api_key )是 taker
        if trade_data.get('owner') == self.config.api_key:
            await self._handle_taker_trade(trade_data)
    
    async def _handle_maker_trade(self, maker_order, taker_asset_id, side):
        """当我是 maker 时，更新我的持仓"""
        size = Decimal(maker_order.get('matched_amount', 0))
        maker_asset_id = maker_order.get('asset_id')
        
        # 判断 maker_asset_id 和 taker_asset_id 是否同一个资产
        if maker_asset_id == taker_asset_id:
            # -------------------------------
            #  同资产：taker 买 => maker 减仓
            #          taker 卖 => maker 加仓
            # -------------------------------
            if side == 'BUY':
                # taker 买 => 我被动卖 => 减少对应资产
                self._update_position(maker_asset_id, -size)
            elif side == 'SELL':
                # taker 卖 => 我被动买 => 增加对应资产
                self._update_position(maker_asset_id, +size)
        else:
            # -------------------------------
            #  不同资产：说明一个是YES,一个是NO
            #   - taker 买 yes => 我被动卖 no => no + 
            #   - taker 卖 yes => 我被动买 no => no - 
            #   - taker 买 no  => 我被动卖 yes => yes +
            #   - taker 卖 no  => 我被动买 yes => yes -
            # -------------------------------
            if side == 'BUY':
                self._update_position(maker_asset_id, +size)
            elif side == 'SELL':
                self._update_position(maker_asset_id, -size)
    
    async def _handle_taker_trade(self, trade_data):
        """当我是 taker 时，更新我的持仓"""
        size = Decimal(trade_data.get('size', 0))
        taker_asset_id = trade_data.get('asset_id')
        side = trade_data.get('side')
        
        if side == 'BUY':
            # taker 买 => +size
            self._update_position(taker_asset_id, +size)
        elif side == 'SELL':
            # taker 卖 => -size
            self._update_position(taker_asset_id, -size)
    
    def _update_position(self, asset_id, delta: Decimal):
        """更新仓位（正值加仓、负值减仓）"""
        if asset_id == self.config.yes_id:
            self.order_book.yes_position += delta
        elif asset_id == self.config.no_id:
            self.order_book.no_position += delta
        else:
            # 如果不在 yes/no 内，看你是否要报错或只是忽略
            logger.warning(f"_update_position: Unknown asset_id {asset_id}, skip.")