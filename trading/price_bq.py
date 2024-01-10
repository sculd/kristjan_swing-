import time, os, datetime, logging, json
import pandas as pd, numpy as np
from collections import defaultdict, deque
import trading.candle
import pytz

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), 'credential.json')
from google.cloud import bigquery


def epoch_seconds_to_datetime(timestamp_seconds):
    t = datetime.datetime.utcfromtimestamp(timestamp_seconds)
    t_tz = pytz.utc.localize(t)
    return t_tz

def _get_epoch_seconds_before(minutes_before):
    now_epoch_seconds = int(time.time() // 60) * 60
    return (now_epoch_seconds - minutes_before * 60)


class PriceBq:
    def __init__(self):
        self.bigquery_client = bigquery.Client()

    def fetch_closes_since_for_symbol(self, since_epoch_seconds):
        logging.debug(f'fetching prices since {since_epoch_seconds}({datetime.datetime.fromtimestamp(since_epoch_seconds)})')

        t_since = epoch_seconds_to_datetime(since_epoch_seconds)
        t_str_since = t_since.strftime("%Y-%m-%d %H:%M:%S %Z")

        query = f"""
            WITH LATEST AS (
            SELECT symbol, timestamp, max(ingestion_timestamp) AS max_ingestion_timestamp
            FROM `trading-290017.market_data_okx.by_minute` 
            WHERE TRUE
            AND timestamp >= "{t_str_since}"
            GROUP BY symbol, timestamp
            )

            SELECT *
            FROM `trading-290017.market_data_okx.by_minute` AS T JOIN LATEST ON T.timestamp = LATEST.timestamp AND T.ingestion_timestamp = LATEST.max_ingestion_timestamp AND T.symbol = LATEST.symbol
            WHERE TRUE
            AND T.timestamp >= "{t_str_since}"
            ORDER BY T.timestamp ASC
        """
        
        symbol_serieses = defaultdict(list)
        symbol_cnts = defaultdict(int)
        bq_query_job = self.bigquery_client.query(query)

        t_zero_epoch = datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
        cnt = 0
        for row in bq_query_job:
            epoch_seconds = (row['timestamp'] - t_zero_epoch).total_seconds()
            symbol_serieses[row["symbol"]].append((epoch_seconds, row['open'], row['high'], row['low'], row['close'], row['volume'],))
            symbol_cnts[row["symbol"]] += 1
            cnt += 1

        logging.info(f'fetched {cnt} rows for {len(list(symbol_cnts.keys()))} symbols, avg {np.mean([cnt for _, cnt in symbol_cnts.items()])} entries per symbol')
        del bq_query_job
        return symbol_serieses

    def fetch_closes_since(self, since_epoch_seconds):
        logging.debug(f'fetching prices since {since_epoch_seconds}({datetime.datetime.fromtimestamp(since_epoch_seconds)})')

        symbol_serieses = self.fetch_closes_since_for_symbol(since_epoch_seconds)
        return symbol_serieses

    def fetch_closes(self, window_minutes):
        logging.info(f'fetching prices for last {window_minutes} minutes')
        epoch_seconds_first = _get_epoch_seconds_before(window_minutes)
        symbol_serieses = self.fetch_closes_since(epoch_seconds_first)
        return symbol_serieses

