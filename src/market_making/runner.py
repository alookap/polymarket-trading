# runner.py
import sys
import asyncio
import logging
import signal
from typing import Optional
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from .websockets_manager import WebsocketManager
from .order_manager import OrderManager
from .orderbook import OrderBook
from .base_market_maker import BaseMarketMaker
from .simplest_market_maker import SimplestMM

from py_clob_client.client import ClobClient, ApiCreds

logger = logging.getLogger(__name__)

class RunnerState(Enum):
    """Runner的状态枚举"""
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class RunnerConfig:
    """Runner配置"""
    private_key: str
    api_key: str
    api_secret: str
    api_passphrase: str
    condition_id: str # market id
    yes_id: str
    no_id: str
    market_ws_endpoint: str
    user_ws_endpoint: str
    agency_address: str
    strategy_interval: float = 1.0
    width: Decimal = Decimal("0.01")
    price_threshold: Decimal = Decimal("0.001")

class MarketMakingRunner:
    """市场做市Runner，负责协调各个组件的运行"""
    
    def __init__(self, config: RunnerConfig):
        self.config = config
        self.state = RunnerState.INITIALIZED
        self._stop_event = asyncio.Event() ### what means
        
        # Initialization
        self.api_client = self._setup_api_client()
        self.order_book = OrderBook(
            self.config.condition_id,
            self.config.yes_id,
            self.config.no_id
        )
        self.order_manager = OrderManager(api_client=self.api_client)
        self.strategy = self._setup_strategy()
        self.ws_manager = self._setup_websocket_manager()
        
        # 设置信号处理
        self._setup_signal_handlers()
        
    def _setup_api_client(self):
        """设置API客户端"""
        host: str = "https://clob.polymarket.com"
        key = self.config.private_key
        chain_id = 137 # Polygen Chain ID
        creds = ApiCreds(
            api_key=self.config.api_key,
            api_secret=self.config.api_secret,
            api_passphrase=self.config.api_passphrase,
        )

        return ClobClient(
            host, 
            key=key, 
            chain_id=chain_id, 
            creds=creds, 
            signature_type=1, 
            funder=self.config.agency_address)
        
    def _setup_strategy(self) -> BaseMarketMaker:
        """设置交易策略"""
        return SimplestMM(
            orderbook=self.order_book,
            market_id=self.config.condition_id,
            yes_asset_id=self.config.yes_id,
            no_asset_id=self.config.no_id,
            width=self.config.width,
            price_threshold=self.config.price_threshold
        )
        
    def _setup_websocket_manager(self) -> WebsocketManager:
        """设置WebSocket管理器"""
        ws_manager = WebsocketManager(
            market_url=self.config.market_ws_endpoint,
            user_url=self.config.user_ws_endpoint,
            api_key=self.config.api_key,
            api_secret=self.config.api_secret,
            api_passphrase=self.config.api_passphrase,
            condition_id=self.config.condition_id,
            yes_id=self.config.yes_id,
            no_id=self.config.no_id
        )
        
        # 添加市场数据处理器
        ws_manager.add_market_handler(self._create_market_handler())
        ws_manager.add_user_handler(self._create_user_handler())
        
        return ws_manager
        
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        if sys.platform == 'win32':
            signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.stop()))
            signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(self.stop()))
        else:
            for sig in (signal.SIGTERM, signal.SIGINT):
                asyncio.get_event_loop().add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(self.stop())
                )
                
    def _create_market_handler(self): ### 需不需要 async def
        """创建市场数据处理器"""
        async def handler(data):
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
                await self.stop()
                
        return handler
        
    def _create_user_handler(self): ### 需不需要async def? 不需要放在这里？
        """创建用户数据处理器"""
        async def handler(data):
            try:
                # 处理订单更新
                if isinstance(data, dict) and 'event_type' in data:
                    await self.order_manager.handle_order_update(data)
                    
                # 更新策略持仓
                new_position = self.order_book.get_total_position()
                self.strategy.update_position(new_position)
                
            except Exception as e:
                logger.error(f"Error in user handler: {e}", exc_info=True)
                await self.stop()
                
        return handler
        
    async def _strategy_loop(self):
        """策略执行循环"""
        logger.info("Starting strategy loop...")
        while not self._stop_event.is_set():
            try:
                # 生成订单
                orders = self.strategy.generate_orders()
                if orders:
                    # 取消现有订单
                    # active_orders = self.order_manager.get_active_orders(
                    #     self.config.condition_id
                    # )
                    # if active_orders:
                    await self.order_manager.cancel_all_orders(self.config.condition_id)
                    
                    # 下新订单
                    for order in orders:
                        order_id = await self.order_manager.place_order(order)
                        logger.info(f"Placed order: {order_id}")
                        
            except Exception as e:
                logger.error(f"Error in strategy loop: {e}", exc_info=True)
                if self.state == RunnerState.RUNNING:
                    await self.stop()
                break
                
            await asyncio.sleep(self.config.strategy_interval)
            
    async def start(self):
        """启动Runner"""
        try:
            logger.info("Starting market making runner...")
            self.state = RunnerState.STARTING
            
            # 启动WebSocket连接
            ws_task = asyncio.create_task(self.ws_manager.start())
            
            # 等待order book初始化完成
            logger.info("Waiting for order book initialization...")
            await self.order_book.initialized.wait()
            logger.info("Order book initialized, starting strategy loop...")
            
            # 启动策略循环
            strategy_task = asyncio.create_task(self._strategy_loop())
            
            self.state = RunnerState.RUNNING
            
            # 等待任务完成或发生错误
            await asyncio.gather(ws_task, strategy_task)
            
        except Exception as e:
            logger.error(f"Error starting runner: {e}", exc_info=True)
            self.state = RunnerState.ERROR
            await self.stop()
            
    async def stop(self):
        """停止Runner"""
        if self.state == RunnerState.STOPPING:
            return
            
        logger.info("Stopping market making runner...")
        self.state = RunnerState.STOPPING
        
        try:
            # 设置停止事件
            self._stop_event.set()
            
            # 取消所有订单
            await self.order_manager.cancel_all_orders(self.config.condition_id)
            
            # 停止WebSocket连接
            await self.ws_manager.stop()
            
            # 关闭线程池
            self.order_manager.executor.shutdown(wait=True)
            
            self.state = RunnerState.STOPPED
            logger.info("Runner stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping runner: {e}", exc_info=True)
            self.state = RunnerState.ERROR
            
    @property
    def is_running(self) -> bool:
        """检查Runner是否在运行"""
        return self.state == RunnerState.RUNNING