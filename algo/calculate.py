import pandas as pd, numpy as np
import ta
import publish.telegram

# Initial value of the trading portfolio in dollars
default_portfolio_value = 100000
# Maximum percentage of the portfolio value to risk on a single trade
default_risk_trade_percentage = 1
# Minimum number of days for an asset to be considered in a consolidation period
default_min_days_in_consolidation = 7
# Maximum number of days for an asset to remain in the consolidation period
default_max_days_in_consolidation = 56
# Minimum percentage increase in asset price to consider for trading
default_min_perc_increase = 3

class KristjanRecoveryTradingParam:
    def __init__(self, risk_trade_percentage, min_days_in_consolidation, max_days_in_consolidation, min_perc_increase):
        self.risk_trade_percentage = risk_trade_percentage
        self.min_days_in_consolidation = min_days_in_consolidation
        self.max_days_in_consolidation = max_days_in_consolidation
        self.min_perc_increase = min_perc_increase

    def get_default_param():
        return KristjanRecoveryTradingParam(
            default_risk_trade_percentage, default_min_days_in_consolidation, default_max_days_in_consolidation, default_min_perc_increase)
    

class Status:
    def __init__(self):
        self.reset()

    def reset(self):
        self.enter_info = None

    def update(self, enter_info):
        self.enter_info = enter_info


def get_enter_info(asset, df, trading_param):
    if len(df) < 90:
        return None
    
    df['SMA_10'] = df['close'].rolling(window=10).mean()
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    df['sma_valid'] = (df['SMA_10'] > df['SMA_20']) & (df['SMA_20'] > df['SMA_50'])

    df['ATR'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()

    for i in df.index[90:-1]:
        if df["high"][i] <= df["high"][i-1] or df["high"][i] <= df["high"][i+1]:
            continue

        publish.telegram.post_message(f'a local high for {asset} was found at {df.iloc[i]}')

        counter_high_broken = 0

        counter_consolidation_time = 0
        increase_30_bars = (df["high"][i] / df["high"][i-30] - 1) * 100
        increase_60_bars = (df["high"][i] / df["high"][i-60] - 1) * 100
        increase_90_bars = (df["high"][i] / df["high"][i-90] - 1) * 100
        
        enter_index = 0
        for e in df.index[i+1:]:
            counter_consolidation_time_maxed = \
                counter_consolidation_time >= trading_param.max_days_in_consolidation

            conditional = counter_high_broken == 0 and \
                df["open"][e] < df["high"][i] and \
                df['sma_valid'][e] and \
                (df['high'][i] - df['low'][e]) < df['ATR'][e-1] and \
                counter_consolidation_time >= trading_param.min_days_in_consolidation and \
                not counter_consolidation_time_maxed and \
                (increase_30_bars > trading_param.min_perc_increase or increase_60_bars > trading_param.min_perc_increase or increase_90_bars > trading_param.min_perc_increase)

            # no way to recoever these conditions for the same i
            if counter_consolidation_time_maxed or counter_high_broken > 0: 
                break

            counter_consolidation_time += 1

            if df["close"][e] < df['SMA_50'][e]:
                break

            if df["high"][e] > df["high"][i]:
                counter_high_broken += 1

            if df["high"][e] > df["high"][i] and conditional:
                enter_index = e
                break

        if enter_index == df.index[-1]:
            return {
                "asset": asset,
                "entry_timestamp": df["timestamp"][e],
                "entry_price": df["close"][e],
                "consolidation_high_price": df["high"][i],
                "consolidation_high_timestamp": df["timestamp"][i],
                "increase_30_bars": increase_30_bars,
                "increase_60_bars": increase_60_bars,
                "increase_90_bars": increase_90_bars,
                "counter_consolidation_time": counter_consolidation_time,
                "stop_loss": df["low"][e],
            }

    return None


def get_exit_info(asset, df, enter_info):
    df['SMA_20'] = df['close'].rolling(window=20).mean()

    def calculate_returns(close_t):
        return {
            "perc_open_returns": (close_t / enter_info["entry_price"] - 1),
            "transported_gain_loss": 0,
        }

    def get_info(exit_price, outcome):
        rts = calculate_returns(exit_price)
        return {
            'asset': asset,
            'entry_timestamp': enter_info["entry_timestamp"],
            'exit_timestamp': df.iloc[-1]["timestamp"],
            'entry_price': enter_info["entry_price"],
            'exit_price': exit_price,
            'outcome': outcome
        }

    if df.iloc[-1]["low"] < enter_info["stop_loss"]:
        # here using df.loc[e, "stop_loss"] seems unrealistic, instead use df.loc[t, "low"]
        exit_price = (enter_info["stop_loss"] + df.iloc[-1]["low"]) / 2.0
        return get_info(exit_price, "Stop Loss")

    if df.iloc[-1]["close"] < df.iloc[-1]['SMA_20']:
        exit_price = df.iloc[-1]["close"]
        return get_info(exit_price, "Trail")

    return None
