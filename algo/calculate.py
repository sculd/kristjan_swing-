import pandas as pd, numpy as np
import ta

def trade_asset(asset, df, portfolio_value, risk_trade_percentage, min_days_in_consolidation, max_days_in_consolidation, min_perc_increase):
    trades = pd.DataFrame(columns=['Asset', 'Entry Date', 'Exit Date', 'Entry Price', 'Exit Price', 'Dollar Return', 'Outcome'])
    open_trades = pd.DataFrame(columns=['Asset', 'Entry Date', 'Entry Price', 'Current Price', 'Stop Loss', 'Potential Dollar Return'])

    df["highest_high"] = False
    df["increase_30_bars"] = 0.0
    df["increase_60_bars"] = 0.0
    df["increase_90_bars"] = 0.0
    df["counter_consolidation_time"] = 0
    df["consolidation_high_price"] = 0.0
    df["consolidation_high_time"] = pd.to_datetime(df['date']).dt.date[0]
    df["perc_open_returns"] = 0.0
    df["dollar_open_returns"] = 0.0
    df["portfolio"] = portfolio_value
    df["position_halved"] = False
    df['SMA_10'] = df['close'].rolling(window=10).mean()
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    df['sma_valid'] = (df['SMA_10'] > df['SMA_20']) & (df['SMA_20'] > df['SMA_50'])
    df['transported_gain_loss'] = 0.0
    df['ATR'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
    df['outcome'] = None
    last_bar = 0

    i, l = 0, len(df)
    #while i < l:
    for i in df.index[last_bar:]:
        if i > 0 and i > last_bar:
            df.loc[i, "portfolio"] = df["portfolio"][i-1]

        if i > 90 and i < (len(df)-1) and df["high"][i] > df["high"][i-1] and df["high"][i] > df["high"][i+1] and i >= last_bar:
            is_trade_closed = False
            counter_high_broken = 0

            df.loc[i, "portfolio"] = df["portfolio"][i-1]
            counter_consolidation_time = 0
            df.loc[i, "highest_high"] = True
            increase_30_bars = (df["high"][i] / df["high"][i- 30] - 1) * 100
            increase_60_bars = (df["high"][i] / df["high"][i- 60] - 1) * 100
            increase_90_bars = (df["high"][i] / df["high"][i- 90] - 1) * 100

            for e in df.index[i+1:]:
                counter_consolidation_time_maxed = \
                    counter_consolidation_time >= max_days_in_consolidation
                    
                conditional = counter_high_broken == 0 and \
                    df["open"][e] < df["high"][i] and \
                    df['sma_valid'][e] and \
                    (df['high'][i] - df['low'][e]) < df['ATR'][e-1] and \
                    counter_consolidation_time >= min_days_in_consolidation and \
                    not counter_consolidation_time_maxed and \
                    (increase_30_bars > min_perc_increase or increase_60_bars > min_perc_increase or increase_90_bars > min_perc_increase) and \
                    e > last_bar
 
                """
                if conditional:
                    print(
                        f"conditional is True, i: {i}, e: {e},"
                        f"df['date'][i]: {df['date'][i]}",
                        f"df['date'][e]: {df['date'][e]}",
                        f"df['open'][e]: {df['open'][e]},"
                        f"df['ATR'][e-1]: {df['ATR'][e-1]},"
                        f"counter_consolidation_time: {counter_consolidation_time},"
                        f"increase_30_bars: {increase_30_bars}"
                        f"increase_60_bars: {increase_60_bars}"
                        f"increase_90_bars: {increase_90_bars}")
                   
                    print(
                        f"conditional is False, i: {i}, e: {e},"
                        f"counter_high_broken == 0: {counter_high_broken == 0},"
                        f"df['open'][e] < df['high'][i]: {df['open'][e] < df['high'][i]},"
                        f"df['sma_valid'][e]: {df['sma_valid'][e]},"
                        f"(df['high'][i] - df['low'][e]) < df['ATR'][e-1]: {(df['high'][i] - df['low'][e]) < df['ATR'][e-1]},"
                        f"counter_consolidation_time >= min_days_in_consolidation: {counter_consolidation_time >= min_days_in_consolidation},"
                        f"counter_consolidation_time < max_days_in_consolidation: {counter_consolidation_time < max_days_in_consolidation},"
                        f"(increase_30_bars > min_perc_increase or increase_60_bars > min_perc_increase or increase_90_bars > min_perc_increase): {(increase_30_bars > min_perc_increase or increase_60_bars > min_perc_increase or increase_90_bars > min_perc_increase)}")
                """

                if is_trade_closed:
                    break

                # no way to recoever these conditions for the same i
                if counter_consolidation_time_maxed or counter_high_broken > 0: break

                if e > last_bar:
                    df.loc[e, "portfolio"] = df["portfolio"][e-1]
                    counter_consolidation_time += 1

                if df["close"][e] < df['SMA_50'][e]:
                    break

                if df["high"][e] > df["high"][i] and conditional:
                    df.loc[e, "consolidation_high_price"] = df["high"][i]
                    df.loc[e, "consolidation_high_time"] = df["date"][i]
                    df.loc[e, "increase_30_bars"] = increase_30_bars
                    df.loc[e, "increase_60_bars"] = increase_60_bars
                    df.loc[e, "increase_90_bars"] = increase_90_bars
                    df.loc[e, "counter_consolidation_time"] = counter_consolidation_time
                    df.loc[e, "stop_loss"] = df["low"][e]

                    for t in df.index[e:]:
                        last_bar = t

                        def calculate_returns(close_t):
                            if t < e+5:
                                df.loc[t, "perc_open_returns"] = (close_t / df["consolidation_high_price"][e] - 1)
                                df.loc[t, "dollar_open_returns"] = (df["perc_open_returns"][t] * df["portfolio"][e])
                                df.loc[t, 'transported_gain_loss'] = 0
                            elif t == e+5:
                                df.loc[t, "perc_open_returns"] = (close_t / df["consolidation_high_price"][e] - 1)
                                df.loc[t, "dollar_open_returns"] = (df["perc_open_returns"][t] * df["portfolio"][e])
                                df.loc[t, 'transported_gain_loss'] = df["dollar_open_returns"][t] / 2
                            else:
                                df.loc[t, "perc_open_returns"] = (close_t / df["consolidation_high_price"][e] - 1) / 2
                                df.loc[t, 'transported_gain_loss'] = df['transported_gain_loss'][t-1]
                                df.loc[t, "dollar_open_returns"] = (df["perc_open_returns"][t] * df["portfolio"][e]) + df['transported_gain_loss'][t]
                            df.loc[t, "portfolio"] = df["portfolio"][e] + df["dollar_open_returns"][t]

                        calculate_returns(df["close"][t])
                        
                        if df["low"][t] < df.loc[e, "stop_loss"]:
                            is_trade_closed = True
                            last_bar = t
                            # here using df.loc[e, "stop_loss"] seems unrealistic
                            calculate_returns(df.loc[t, "low"])
                            
                            exit_date = df["date"][t]
                            exit_price = df.loc[e, "stop_loss"]
                            dollar_return = df["dollar_open_returns"][t]
                            df.loc[t, "outcome"] = "Stop loss"

                            new_trade = pd.DataFrame({
                                'Asset': [asset],
                                'Entry Date': [df["date"][e]],
                                'Exit Date': [exit_date],
                                'Entry Price': [df["consolidation_high_price"][e]],
                                'Exit Price': [exit_price],
                                'Dollar Return': [dollar_return],
                                'Outcome': "Stop Loss"
                            })

                            # Append the new trade to the trades DataFrame
                            trades = pd.concat([trades, new_trade], ignore_index=True)
                            break

                        if df["close"][t] < df['SMA_20'][t]:
                            is_trade_closed = True
                            last_bar = t
                            df.loc[t, "portfolio"] = df["portfolio"][e] + df["dollar_open_returns"][t]
                            exit_date = df["date"][t]
                            exit_price = df["close"][t]
                            dollar_return = df["dollar_open_returns"][t]
                            df.loc[t, "outcome"] = "Trail"
                            
                            new_trade = pd.DataFrame({
                                'Asset': [asset],
                                'Entry Date': [df["date"][e]],
                                'Exit Date': [exit_date],
                                'Entry Price': [df["consolidation_high_price"][e]],
                                'Exit Price': [exit_price],
                                'Dollar Return': [dollar_return],
                                'Outcome': "Trail"
                            })
                            # Append the new trade to the trades DataFrame
                            trades = pd.concat([trades, new_trade], ignore_index=True)
                            break

                        if t == len(df)-1:
                        # Add a new entry to open_trades DataFrame
                            open_trade_entry = {
                                'Asset': asset,
                                'Entry Date': df["date"][e],
                                'Entry Price': df["consolidation_high_price"][e],
                                'Current Price': df["close"][e],
                                'Stop Loss': df["low"][e],
                                'Potential Dollar Return': df["dollar_open_returns"][t]
                            }
                            open_trade_index = len(open_trades)
                            open_trades.loc[open_trade_index] = [asset, df["date"][e], df["consolidation_high_price"][e], df["close"][e], df["low"][e], df["dollar_open_returns"][t]]

                if df["high"][e] > df["high"][i]:
                    counter_high_broken += 1

        #i = max(i+1, last_bar+1)

    return df, trades, open_trades