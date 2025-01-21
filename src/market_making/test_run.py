# test_run.py
import asyncio
import logging
import os
from decimal import Decimal
from dotenv import load_dotenv

from .runner import MarketMakingRunner, RunnerConfig

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
    )

async def main():
    # 加载环境变量（如果你用 dotenv）
    load_dotenv()
    setup_logging()

    # 从环境变量读取（或者直接硬编码）
    PRIVATE_KEY = os.getenv("PK", "0x...")
    AGENCY_ADDRESS = os.getenv("AGENCY_ADDRESS", "0x...")
    API_KEY = os.getenv("CLOB_API_KEY")
    API_SECRET = os.getenv("CLOB_SECRET")
    API_PASS = os.getenv("CLOB_PASS_PHRASE")
    # CONDITION_ID = os.getenv("CONDITION_ID")
    # YES_ID = os.getenv("YES_ID")
    # NO_ID = os.getenv("NO_ID")

    CONDITION_ID = "0x8d52fed4ae101977e7807fe97c503bb0124c8a9947e02dd8507b3191bf220d87"
    YES_ID = "111098511815305333461136150460272626183935263570250422706652341149027899261464"
    NO_ID = "6075043278597420473413557525708711172563536710949920834070346067873777894873"

    # 创建配置
    config = RunnerConfig(
        private_key=PRIVATE_KEY,
        api_key=API_KEY,
        api_secret=API_SECRET,
        api_passphrase=API_PASS,
        condition_id=CONDITION_ID,
        yes_id=YES_ID,
        no_id=NO_ID,
        market_ws_endpoint="wss://ws-subscriptions-clob.polymarket.com/ws/market",
        user_ws_endpoint="wss://ws-subscriptions-clob.polymarket.com/ws/user",
        agency_address=AGENCY_ADDRESS,
        strategy_interval=1.0,
        width=Decimal("0.01"),
        price_threshold=Decimal("0.001")
    )

    # 实例化 runner
    runner = MarketMakingRunner(config)

    # 启动
    try:
        await runner.start()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Stopping the runner...")
    finally:
        await runner.stop()

if __name__ == "__main__":
    asyncio.run(main())
