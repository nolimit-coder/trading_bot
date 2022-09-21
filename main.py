import schedule
import time
from trading_bot import TradingBot
from config import *


def run_bot(trading_bot):
    df = trading_bot.load_data(PAIR, TIMEFRAME, limit=250)
    df = trading_bot.load_indicators(df)

    if trading_bot.should_long(df):
        trading_bot.create_long_order(df)
    elif trading_bot.should_short(df):
        trading_bot.create_short_order(df)


trading_bot = TradingBot(EXCHANGE, API_KEY, SECRET)
schedule.every().hour.at(":00").do(run_bot, trading_bot=trading_bot)

while trading_bot.exchange.fetchStatus()["status"] == "ok":
    schedule.run_pending()
    time.sleep(1)
