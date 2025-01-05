# main.py
import asyncio
import os
import logging
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

from runner import MarketMakingRunner, RunnerConfig

# 设置日志
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "market_maker.log")
        ]
    )

async def main():
    # 加载环境变量
    load_dotenv()
    
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 创建配置
    config = RunnerConfig(
        api_key=os.getenv("CLOB_API_KEY"),
        api_secret=os.getenv("CLOB_SECRET"),
        api_passphrase=os.getenv("CLOB_PASS_PHRASE"),
        condition_id=os.getenv("CONDITION_ID"),
        yes_id=os.getenv("YES_ID"),
        no_id=os.getenv("NO_ID"),
        market_ws_endpoint="wss://ws-subscriptions-clob.polymarket.com/ws/market",
        user_ws_endpoint="wss://ws-subscriptions-clob.polymarket.com/ws/user",
        strategy_interval=1.0,
        width=Decimal("0.01"),
        price_threshold=Decimal("0.001")
    )
    
    # 创建并启动Runner
    runner = MarketMakingRunner(config)
    
    try:
        await runner.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        await runner.stop()

if __name__ == "__main__":
    asyncio.run(main())