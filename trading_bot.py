import ccxt
import datetime
import pandas as pd
from ta.trend import PSARIndicator, ema_indicator, MACD
import matplotlib.pyplot as plt
import numpy as np

from config import PAIR


class TradingBot:
    def __init__(self, exchange_id, api_key=None, secret=None, is_sandbox=False):
        self.exchange = getattr(ccxt, exchange_id)
        self.exchange = self.exchange(
            {
                "apiKey": api_key,
                "secret": secret,
            }
        )
        self.exchange.set_sandbox_mode(is_sandbox)

    def load_data(self, symbol, timeframe, since=None, limit=None):
        self.exchange.load_markets()
        data = self.exchange.fetch_ohlcv(
            symbol=symbol, timeframe=timeframe, since=since, limit=limit
        )
        dataframe = pd.DataFrame(
            data, columns=["Time", "Open", "High", "Low", "Close", "Volume"]
        )
        dataframe["Time"] = [
            datetime.datetime.fromtimestamp(float(time) / 1000)
            for time in dataframe["Time"]
        ]
        return dataframe

    def load_indicators(self, dataframe):
        macd = MACD(dataframe["Close"])
        dataframe["MACD_LINE"] = macd.macd()
        dataframe["MACD_SIGNAL"] = macd.macd_signal()
        dataframe["MACD_DIFF"] = macd.macd_diff()

        psar = PSARIndicator(dataframe["High"], dataframe["Low"], dataframe["Close"])
        dataframe["PSAR_UP"] = psar.psar_up()
        dataframe["PSAR_DOWN"] = psar.psar_down()
        dataframe["EMA"] = ema_indicator(dataframe["Close"], window=200)
        return dataframe

    def should_long(self, df):
        last_idx = len(df.index) - 1
        prev_idx = last_idx - 1
        is_psar_down_defined = not np.isnan(df["PSAR_DOWN"][last_idx])
        open_orders = self.exchange.fetch_open_orders(symbol=PAIR)
        return (
            len(open_orders) == 0
            and is_psar_down_defined
            and df["MACD_LINE"][last_idx] < 0
            and df["MACD_LINE"][last_idx] > df["MACD_SIGNAL"][last_idx]
            and df["MACD_LINE"][prev_idx] < df["MACD_SIGNAL"][prev_idx]
            and df["Close"][last_idx] > df["EMA"][last_idx]
            and df["Close"][last_idx] > df["PSAR_DOWN"][last_idx]
        )

    def should_short(self, df):
        last_idx = len(df.index) - 1
        prev_idx = last_idx - 1
        is_psar_up_defined = not np.isnan(df["PSAR_UP"][last_idx])
        open_orders = self.exchange.fetch_open_orders(symbol=PAIR)
        return (
            len(open_orders) == 0
            and is_psar_up_defined
            and df["MACD_LINE"][last_idx] > 0
            and df["MACD_LINE"][last_idx] < df["MACD_SIGNAL"][last_idx]
            and df["MACD_LINE"][prev_idx] > df["MACD_SIGNAL"][prev_idx]
            and df["Close"][last_idx] < df["EMA"][last_idx]
            and df["Close"][last_idx] < df["PSAR_UP"][last_idx]
        )

    def create_long_order(self, df):
        last_idx = len(df.index)
        close_price = df["Close"][last_idx]
        psar_down = df["PSAR_DOWN"][last_idx]
        params = {
            "stopLoss": {
                "type": "market",
                "stopLossPrice": psar_down,
            },
            "takeProfit": {
                "type": "market",
                "takeProfitPrice": 2 * close_price - psar_down,
            },
        }
        usdt_balance = self.exchange.fetch_balance()["USDT"]["free"]
        quantity = float("{:.4f}".format(usdt_balance / close_price))
        try:
            order = self.exchange.create_order(
                PAIR,
                type="market",
                side="buy",
                amount=quantity,
                params=params,
            )
            print(
                f"{quantity} BTC have been ordered at {quantity * close_price}$. Stop loss price = {psar_down}, take profit price = {2 * close_price - psar_down} . Current balance: {usdt_balance}"
            )
        except Exception as e:
            print(f"create_long_order() failed: {e}")

    def create_short_order(self, df):
        last_idx = len(df.index)
        close_price = df["Close"][last_idx]
        psar_up = df["PSAR_UP"][last_idx]
        usdt_balance = self.exchange.fetch_balance()["USDT"]["free"]
        margin_balance = self.exchange.fetch_balance({"type": "margin"})
        quantity_to_borrow = float("{:.4f}".format(usdt_balance / close_price))

        if margin_balance <= 0:
            if usdt_balance <= 0:
                print(
                    "create_short_order() failed: Margin account empty and no USDT in spot account."
                )
                return
            self.exchange.transfer("USDT", usdt_balance, "spot", "margin")
        try:
            self.exchange.sapi_post_margin_loan(
                {"symbol": PAIR, "amount": quantity_to_borrow, "isIsolated": True}
            )

            self.exchange.sapi_post_margin_order_oco(
                {
                    "symbol": PAIR,
                    "side": "BUY",
                    "isIsolated": True,
                    "quantity": quantity_to_borrow,
                    "price": psar_up,
                    "stopPrice": close_price - psar_up,
                    "stopLimitPrice": close_price - psar_up,
                    "stopLimitTimeInForce": "GTC",
                    "sideEffectType": "AUTO_REPAY",
                }
            )
        except Exception as e:
            print(f"create_short_order() failed: {e}")

    def plot_data(self, dataframe):
        dataframe.plot(x="Time", y=["Close", "EMA", "PSAR_UP", "PSAR_DOWN"])
        dataframe.plot(x="Time", y=["MACD_LINE", "MACD_SIGNAL", "MACD_DIFF"])
        plt.show()
