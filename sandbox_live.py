import logging, sys, datetime
import trading.price


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler("logs/{}.log".format("log_live")),
        logging.StreamHandler(sys.stdout)
    ]
)


from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

import trading.trade, trading.execution_okx

trade_execution = trading.execution_okx.TradeExecution(target_betsize=200, leverage=5)
trading_manager = trading.trade.TradeManager(trade_execution=trade_execution)
#trading_manager = trading.trade.TradeManager()


price_cache = trading.price.PriceCache(trading_manager, 130)


logging.info(f"### starting a new kristijan_swing live at {datetime.datetime.now()}")

import publish.telegram
publish.telegram.post_message(f"starting a new kristijan_swing live at {datetime.datetime.now()}")

import time

while True:
    trading_manager.trade_execution.print()
    time.sleep(60)
