import pandas as pd, numpy as np, datetime
import pytz
import logging

import algo.calculate
import trading.execution
from collections import defaultdict


def epoch_seconds_to_datetime(timestamp_seconds):
    t = datetime.datetime.utcfromtimestamp(timestamp_seconds)
    t_tz = pytz.utc.localize(t)
    return t_tz

class TradeManager:
    def __init__(self, trading_param=None, trade_execution=None):
        self.trading_param = trading_param if trading_param is not None else algo.calculate.KristjanRecoveryTradingParam.get_default_param()
        self.trade_execution = trade_execution if trade_execution else trading.execution.TradeExecution()
        self.status_per_symbol = defaultdict(algo.calculate.Status)

    def on_new_minutes(self, symbol, timestamp_epoch_seconds, df):
        '''
        timestamp_epochs_values is an arrya of (timestamp, value) tuples.
        '''
        #get_enter_info(asset, df, trading_param)
        enter_info_before = self.status_per_symbol[symbol].enter_info
        if enter_info_before is None:
            enter_info = algo.calculate.get_enter_info(symbol, df, self.trading_param)
            self.status_per_symbol[symbol].update(enter_info)
            if enter_info is not None:
                logging.info(f'enter_info is found non-None at {epoch_seconds_to_datetime(timestamp_epoch_seconds)} for {symbol}')
                self.trade_execution.execute(symbol, timestamp_epoch_seconds, df.iloc[-1]['close'], 1, 1)
        else:
            exit_info = algo.calculate.get_exit_info(symbol, df, enter_info_before)
            if exit_info is None:
                return
            
            logging.info(f'exit_info is found non-None at {epoch_seconds_to_datetime(timestamp_epoch_seconds)}: {exit_info}')
            self.status_per_symbol[symbol].update(None)
            self.trade_execution.execute(symbol, timestamp_epoch_seconds, df.iloc[-1]['close'], 1, -1)
