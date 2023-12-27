import pandas as pd
from binance import Client
import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import ta

def strategy_backtest(data, portfolio_value, risk_trade_percentage, min_days_in_consolidation, max_days_in_consolidation, min_perc_increase):
	trades = pd.DataFrame(columns=['Asset', 'Entry Date', 'Exit Date', 'Entry Price', 'Exit Price', 'Dollar Return', 'Outcome'])
	open_trades = pd.DataFrame(columns=['Asset', 'Entry Date', 'Entry Price', 'Current Price', 'Stop Loss', 'Potential Dollar Return'])
	for asset, df in data.items():
		df["highest_high"] = False
		df["increase_30_bars"] = 0.0
		df["increase_60_bars"] = 0.0
		df["increase_90_bars"] = 0.0
		df["counter_consolidation_time"] = 0
		df["consolidation_high_price"] = 0.0
		df["consolidation_high_time"] = pd.to_datetime(df['date']).dt.date[0]
		df["perc_open_returns"] = 0.0
		df["dollar_open_returns"] = 0.0
		df["portfolio"] = float(portfolio_value / len(data))
		df["position_halved"] = False
		df['SMA_10'] = df['close'].rolling(window=10).mean()
		df['SMA_20'] = df['close'].rolling(window=20).mean()
		df['SMA_50'] = df['close'].rolling(window=50).mean()
		df['sma_valid'] = (df['SMA_10'] > df['SMA_20']) & (df['SMA_20'] > df['SMA_50'])
		df['transported_gain_loss'] = 0.0
		df['ATR'] = ta.volatility.AverageTrueRange(df['high'],
		df['low'], df['close']).average_true_range()
		df['outcome'] = None
		last_bar = 0

		for i in df.index[last_bar:]:
			if i > 0 and i > last_bar:
				df.loc[i, "portfolio"] = df["portfolio"][i-1]
			if i > 90 and i < (len(df)-1) and df["high"][i] > df["high"][i-1] and df["high"][i] > df["high"][i+1] and i >= last_bar:
				consolidation_invalid = False
				counter_high_broken = 0

				df.loc[i, "portfolio"] = df["portfolio"][i-1]
				counter_consolidation_time = 0
				df.loc[i, "highest_high"] = True
				increase_30_bars = (df["high"][i] / df["high"][i- 30] - 1) * 100
				increase_60_bars = (df["high"][i] / df["high"][i- 60] - 1) * 100
				increase_90_bars = (df["high"][i] / df["high"][i- 90] - 1) * 100
				for e in df.index[i+1:]:
					conditional = counter_high_broken == 0 and \
                        df["open"][e] < df["high"][i] and \
                        df['sma_valid'][e] and \
                        (df["high"][i] - df["low"][e]) < df['ATR'][e-1] and \
                        counter_consolidation_time >= min_days_in_consolidation and \
                        counter_consolidation_time < max_days_in_consolidation and \
                        (increase_30_bars > min_perc_increase or increase_60_bars > min_perc_increase or increase_90_bars > min_perc_increase) and \
                        e > last_bar

					if consolidation_invalid:
						break

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
							df.loc[t, "portfolio"] = df["portfolio"][e] + df["dollar_open_returns"][t]
							df.loc[t, "perc_open_returns"] = df["close"][t] / df["consolidation_high_price"][e] - 1
							df.loc[t, "dollar_open_returns"] = df["perc_open_returns"][t] * df["portfolio"][e]
                            
							if t == e+5:
								df.loc[t, "position_halved"] = True
								df.loc[t, "perc_open_returns"] = (df["close"][t] / df["consolidation_high_price"][e] - 1)
								df.loc[t, "dollar_open_returns"] = (df["perc_open_returns"][t] * df["portfolio"][e])
								df.loc[t, 'transported_gain_loss'] = df["dollar_open_returns"][t] / 2
								df.loc[t, "portfolio"] = df["portfolio"][e] + df["dollar_open_returns"][t]
                                
							if t > e+5:
								df.loc[t, 'transported_gain_loss'] = df['transported_gain_loss'][t-1]
								df.loc[t, "perc_open_returns"] = (df["close"][t] / df["consolidation_high_price"][e] - 1) / 2
								df.loc[t, "dollar_open_returns"] = (df["perc_open_returns"][t] * df["portfolio"][e]) + df['transported_gain_loss'][t]
								df.loc[t, "portfolio"] = df["portfolio"][e] + df["dollar_open_returns"][t]
                                
							if df["low"][t] < df.loc[e, "stop_loss"]:
								consolidation_invalid = True
								last_bar = t
								df.loc[t, "perc_open_returns"] = df.loc[e, "stop_loss"] / df["consolidation_high_price"][e] - 1
								df.loc[t, "dollar_open_returns"] = (df["perc_open_returns"][t] * df["portfolio"][e]) + df['transported_gain_loss'][t]
								df.loc[t, "portfolio"] = df["portfolio"][e] + df["dollar_open_returns"][t]
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
								consolidation_invalid = True
								last_bar = t
								df.loc[t, "portfolio"] = df["portfolio"][e] + df["dollar_open_returns"][t]
								exit_date = df["date"][t]
								exit_price = df["close"][t]
								dollar_return = df["dollar_open_returns"][t]
								df.loc[t, "outcome"] = "Trail"
								new_trade = pd.DataFrame({
									'Asset': [asset],
									'Entry Date': [df["date"]
									[e]],
									'Exit Date': [exit_date],
									'Entry Price':
									[df["consolidation_high_price"][e]],
									'Exit Price': [exit_price],
									'Dollar Return':
									[dollar_return],
									'Outcome': "Trail"
								})
								# Append the new trade to the trades DataFrame
								trades = pd.concat([trades,
								new_trade], ignore_index=True)
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

	# Sort trades DataFrame by 'Entry Date'
	trades.sort_values(by='Entry Date', inplace=True)
	# Create a figure for individual portfolio plots
	plt.figure(figsize=(12, 8))
	# Initialize a DataFrame to store aligned portfolio values for all assets
	all_portfolios = pd.DataFrame()

	# Plot portfolio value for each asset and align for average	calculation
	for asset, df in data.items():
		plt.plot(df['date'], df['portfolio'], label=f'{asset}')
		all_portfolios[asset] = df.set_index('date')['portfolio']
	all_portfolios.fillna(float(portfolio_value / len(data)), inplace=True)

	# Configure the individual portfolio plot
	plt.title('Individual Portfolio Performance by Asset')
	plt.xlabel('Date')
	plt.ylabel('Portfolio Value')

	plt.legend()
	plt.grid(True)
	plt.show() # Show the plot for individual portfolios
	# Create a new figure for the average portfolio plot
	plt.figure(figsize=(12, 8))
	# Calculate the average portfolio value
	all_portfolios['Average Portfolio'] = all_portfolios.sum(axis=1)
	# Plot the average portfolio value
	plt.plot(all_portfolios.index, all_portfolios['Average Portfolio'], label='Average Portfolio', color='black', linewidth=2)

	# Configure the average portfolio plot
	plt.title('Average Portfolio Performance')
	plt.xlabel('Date')
	plt.ylabel('Average Portfolio Value')
	plt.legend()
	plt.grid(True)
	plt.show()

	return trades, open_trades, all_portfolios, data


######################################################
# USER INPUT SECTION
######################################################
# Binance API Settings
# ---------------------
# Provide your Binance API key and secret key below.
# These keys are necessary to access financial data through the Binance API.
API_KEY = 'your_binance_api_key_here'
SECRET_API_KEY = 'your_binance_secret_key_here'


# Trading Portfolio and Strategy Settings
# ---------------------------------------
# Define your initial portfolio value, risk percentage per trade, and
# parameters for the trading strategy's consolidation period and minimum
# percentage increase for asset selection.
# These settings will influence how the trading strategy operates.

# Initial value of the trading portfolio in dollars
portfolio_value = 100000
# Maximum percentage of the portfolio value to risk on a single trade
risk_trade_percentage = 1
# Minimum number of days for an asset to be considered in a consolidation period
min_days_in_consolidation = 7
# Maximum number of days for an asset to remain in the consolidation period
max_days_in_consolidation = 56
# Minimum percentage increase in asset price to consider for trading
min_perc_increase = 30

# Fetching and Analyzing Market Data
# ----------------------------------
# Fetch market data for a predefined list of assets from Binance and
# perform strategy backtesting based on the specified parameters.
# This process will gather historical data for each asset and apply the
# trading strategy to analyze potential trades.
# Connect to Binance using API keys
client = connect_to_binance(API_KEY, SECRET_API_KEY)

# List of cryptocurrency pairs to analyze
selected_assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",\
	"XRPUSDT", "ADAUSDT", "AVAXUSDT", "DOGEUSDT",\
	"DOTUSDT", "TRXUSDT", "LINKUSDT", "MATICUSDT",\
	"LTCUSDT", "UNIUSDT", "BCHUSDT", "ICPUSDT",\
	"XLMUSDT", "NEARUSDT", "ATOMUSDT","INJUSDT"]

def connect_to_binance(API_KEY, SECRET_API_KEY):
	return Client(API_KEY, SECRET_API_KEY)

def get_spot_data(client, timeframe, days_range, selected_assets):
	spot_data = {}

	# Get the current date
	today_date = datetime.date.today()
	# Calculate the trade date for the specified number of days in the past

	trade_date_data = today_date - relativedelta(days=days_range)

	# Store the arguments for the get_historical_klines() method in variables
	timeframe_for_data = timeframe
	start_date_for_data = str(trade_date_data)

	# Loop through the selected symbols and get the daily data for each one
	for symbol in selected_assets:
		print(f"Extracting data for: {symbol}")
		# Initialize an empty list to store the data for the
		symbol
		symbol_data = []

		# Get the daily data for the symbol
		data = client.get_historical_klines(symbol, timeframe_for_data, start_date_for_data)

		# Loop through the daily data and extract the relevant information
		for daily_data in data:
			# Extract the timestamp, open price, high price, low price, close price, and volume
			timestamp, open_price, high_price, low_price, close_price, volume = daily_data[:6]

			# Convert the timestamp to a date
			date = datetime.datetime.fromtimestamp(int(timestamp) / 1000)
			# Add the cleaned data to the list
			symbol_data.append({
				'date': date,
				'asset': symbol,
				'open': float(open_price),
				'high': float(high_price),
				'low': float(low_price),
				'close': float(close_price),
				'volume': float(volume)
			})

		# Convert the data for the symbol to a dataframe
		spot_data[symbol] = pd.DataFrame(symbol_data)

		print(f"Finished Extracting data for: {symbol}")

	return spot_data

# Fetch historical spot data for selected assets
data = get_spot_data(client, "1d", 3000, selected_assets)

# Perform backtest of the trading strategy with the fetched data
closed_trades, open_trades, all_portfolios, data = strategy_backtest(data, portfolio_value, risk_trade_percentage, min_days_in_consolidation, max_days_in_consolidation, min_perc_increase)
