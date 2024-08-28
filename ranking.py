import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

# Define the backtesting function
def backtest_strategy(ticker, start_date, end_date, short_window, long_window):
    # Fetch historical data
    data = yf.download(ticker, start=start_date, end=end_date)
    
    # Calculate short and long moving averages
    data['Short_MA'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
    data['Long_MA'] = data['Close'].rolling(window=long_window, min_periods=1).mean()
    
    # Generate signals
    data['Signal'] = 0
    data['Signal'][short_window:] = np.where(data['Short_MA'][short_window:] > data['Long_MA'][short_window:], 1, 0)
    data['Position'] = data['Signal'].diff()
    
    # Plot data and signals
    plt.figure(figsize=(12,8))
    plt.plot(data['Close'], label='Close Price', alpha=0.5)
    plt.plot(data['Short_MA'], label=f'Short {short_window}-day MA', alpha=0.75)
    plt.plot(data['Long_MA'], label=f'Long {long_window}-day MA', alpha=0.75)
    
    # Plot buy signals
    plt.plot(data[data['Position'] == 1].index, data['Short_MA'][data['Position'] == 1], '^', markersize=10, color='g', label='Buy Signal')
    
    # Plot sell signals
    plt.plot(data[data['Position'] == -1].index, data['Short_MA'][data['Position'] == -1], 'v', markersize=10, color='r', label='Sell Signal')
    
    plt.title(f'{ticker} Trading Strategy Backtest')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend(loc='best')
    plt.grid(True)
    plt.show()

# Example usage
ticker = 'AAPL'  # Apple Inc.
start_date = '2022-01-01'
end_date = '2023-01-01'
short_window = 40
long_window = 100

backtest_strategy(ticker, start_date, end_date, short_window, long_window)
