import pandas as pd
import numpy as np

import vectorbt as vbt

start = "12 month ago UTC"
end = "now UTC"
interval = "30m"
data = vbt.BinanceData.download("BTCUSDT", start=start, end=end, interval=interval)
btc_price_high = data.get("High")
btc_price_low = data.get("Low")
btc_price_close = data.get("Close")


def compute_indicators(close, low, high, ema_window=200):
    macd = vbt.ta("MACD").run(close).macd.squeeze()
    macd_signal = vbt.ta("MACD").run(close).macd_signal.squeeze()
    macd_diff = vbt.ta("MACD").run(close).macd_diff.squeeze()
    psar_up = vbt.ta("PSARIndicator").run(high, low, close).psar_up.squeeze()
    psar_down = vbt.ta("PSARIndicator").run(high, low, close).psar_down.squeeze()
    ema = vbt.ta("EMAIndicator").run(close, ema_window).ema_indicator.squeeze()
    df = pd.DataFrame(
        {
            "PRICE": close,
            "MACD": macd,
            "MACD_SIGNAL": macd_signal,
            "MACD_DIFF": macd_diff,
            "PSAR_UP": psar_up,
            "PSAR_DOWN": psar_down,
            "EMA": ema,
        }
    )
    df["MACD_PREV"] = df.MACD.shift(1)
    df["MACD_SIGNAL_PREV"] = df.MACD_SIGNAL.shift(1)
    conditions = [
        (df["PRICE"] > df["EMA"])
        & (df["PRICE"] > df["PSAR_UP"])
        & (df["MACD"] > df["MACD_SIGNAL"])
        & (df["MACD"] < 0)
        & (df["MACD_PREV"] < df["MACD_SIGNAL_PREV"]),
        (df["PRICE"] < df["EMA"])
        & (df["PRICE"] < df["PSAR_DOWN"])
        & (df["MACD"] < df["MACD_SIGNAL"])
        & (df["MACD"] > 0)
        & (df["MACD_PREV"] > df["MACD_SIGNAL_PREV"]),
    ]
    choices = [1, -1]
    df["BUY"] = np.select(conditions, choices, default=0)
    return df


def combination_indicators(close, low, high, ema_window=200):
    return compute_indicators(close, low, high, ema_window)["BUY"]


ind = vbt.IndicatorFactory(
    input_names=["close", "low", "high"],
    param_names=["window"],
    output_names=["output"],
).from_apply_func(
    combination_indicators,
    close=btc_price_close,
    low=btc_price_low,
    high=btc_price_high,
    window=200,
    keep_pd=True,
    to_2d=False,
)

entries = ind.run(btc_price_close, btc_price_low, btc_price_high)

long_entries = entries.output == 1.0
short_entries = entries.output == -1.0

all_indicators = compute_indicators(btc_price_close, btc_price_low, btc_price_high)


all_indicators["TAKE_PROFIT_LONG"] = (
    all_indicators["PRICE"] - all_indicators["PSAR_UP"]
) / (all_indicators["PRICE"])

all_indicators["TAKE_PROFIT_SHORT"] = (
    all_indicators["PSAR_DOWN"] - all_indicators["PRICE"]
) / (all_indicators["PRICE"])

conditions = [
    (np.isnan(all_indicators["TAKE_PROFIT_SHORT"].values)),
    (np.isnan(all_indicators["TAKE_PROFIT_LONG"].values)),
]
choices = [all_indicators["TAKE_PROFIT_LONG"], all_indicators["TAKE_PROFIT_SHORT"]]

all_indicators["TAKE_PROFIT"] = np.select(conditions, choices)


pf = vbt.Portfolio.from_signals(
    btc_price_close,
    entries=long_entries,
    short_entries=short_entries,
    tp_stop=all_indicators["TAKE_PROFIT"],
    sl_stop=all_indicators["TAKE_PROFIT"],
    upon_opposite_entry="Ignore",
)
holding = pf.from_holding(btc_price_close)

print(holding.stats())
print(pf.stats())

fig = btc_price_close.vbt.plot(trace_kwargs=dict(name="Close"))
vbt.ta("MACD").run(btc_price_close).macd.vbt.plot(
    trace_kwargs=dict(name="MACD"), fig=fig
)
vbt.ta("MACD").run(btc_price_close).macd_signal.vbt.plot(
    trace_kwargs=dict(name="MACD_SIGNAL"), fig=fig
)

vbt.ta("PSARIndicator").run(
    btc_price_high, btc_price_low, btc_price_close
).psar_up.vbt.plot(trace_kwargs=dict(name="PSAR_UP"), fig=fig)

vbt.ta("PSARIndicator").run(
    btc_price_high, btc_price_low, btc_price_close
).psar_down.vbt.plot(trace_kwargs=dict(name="PSAR_DOWN"), fig=fig)

vbt.ta("EMAIndicator").run(btc_price_close).ema_indicator.vbt.plot(
    trace_kwargs=dict(name="EMA"), fig=fig
)

pf.positions.plot(close_trace_kwargs=dict(visible=False), fig=fig).show()
pf.plot().show()
