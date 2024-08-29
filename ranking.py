import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

def calculate_buy_and_hold_return(start_price, end_price):
    return (end_price - start_price) / start_price

def calculate_annualized_return(total_return_percent, days):
    return ((1 + total_return_percent / 100) ** (365 / days) - 1) * 100

def calculate_annualized_buy_and_hold_return(start_price, end_price, days):
    buy_and_hold_return = calculate_buy_and_hold_return(start_price, end_price)
    return calculate_annualized_return(buy_and_hold_return * 100, days)

def backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, strategy, start_with_position):
    all_results = []
    
    for ticker in tickers:
        try:
            # Fetch historical data
            data = yf.download(ticker, start=start_date, end=end_date)
            if data.empty:
                st.error(f"No data fetched for ticker {ticker}.")
                continue
            
            # Calculate moving averages
            data['SMA1'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
            data['SMA2'] = data['Close'].rolling(window=medium_window, min_periods=1).mean()
            data['SMA3'] = data['Close'].rolling(window=long_window, min_periods=1).mean()
            
            # Buy-and-Hold Return
            start_price = data['Close'].iloc[0]
            end_price = data['Close'].iloc[-1]
            buy_and_hold_return = calculate_buy_and_hold_return(start_price, end_price)
            
            # Generate signals based on selected strategy
            if strategy == 'Cross between price and SMA 1':
                data['Signal'] = 0
                data['Signal'][short_window:] = np.where(data['Close'][short_window:] > data['SMA1'][short_window:], 1, 0)
                data['Position'] = data['Signal'].diff()
            elif strategy == 'Cross between SMA 1 and SMA 2':
                data['Signal'] = 0
                data['Signal'][medium_window:] = np.where(data['SMA1'][medium_window:] > data['SMA2'][medium_window:], 1, 0)
                data['Position'] = data['Signal'].diff()
            elif strategy == 'Cross between SMAs 1, 2 and 3':
                data['Signal'] = 0
                bullish_alignment = (data['SMA1'] > data['SMA2']) & (data['SMA2'] > data['SMA3'])
                bearish_alignment = (data['SMA1'] < data['SMA2']) & (data['SMA2'] < data['SMA3'])
                data['Signal'] = np.where(bullish_alignment, 1, 0)
                data['Signal'] = np.where(bearish_alignment, -1, data['Signal'])
                data['Position'] = data['Signal'].diff()
            
            # Initialize variables for trade tracking
            trades = []
            current_position = 1 if start_with_position else 0
            entry_price = data['Close'].iloc[0] if start_with_position else 0
            
            # Track trades based on signals
            for i in range(1, len(data)):
                if data['Position'].iloc[i] == 1 and current_position == 0:  # Buy signal
                    entry_price = data['Close'].iloc[i]
                    current_position = 1
                elif data['Position'].iloc[i] == -1 and current_position == 1:  # Sell signal
                    exit_price = data['Close'].iloc[i]
                    trade_return = (exit_price - entry_price) / entry_price
                    trades.append(trade_return)
                    current_position = 0
            
            # Handle remaining position
            if current_position == 1:
                final_price = data['Close'].iloc[-1]
                trade_return = (final_price - entry_price) / entry_price
                trades.append(trade_return)
            
            # Calculate total return from all trades
            total_return = sum(trades)
            
            # Calculate the number of days in the backtest period
            days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
            if days == 0:
                days = 1  # Avoid division by zero
            
            # Calculate annualized returns
            annualized_return = calculate_annualized_return(total_return * 100, days)
            annualized_buy_and_hold_return = calculate_annualized_buy_and_hold_return(start_price, end_price, days)
            
            # Calculate ratios
            if buy_and_hold_return != 0:
                total_to_buy_and_hold_ratio = total_return / buy_and_hold_return
            else:
                total_to_buy_and_hold_ratio = np.nan  # Handle division by zero

            if annualized_buy_and_hold_return != 0:
                annualized_to_buy_and_hold_ratio = annualized_return / annualized_buy_and-hold_return
            else:
                annualized_to_buy_and_hold_ratio = np.nan  # Handle division by zero
            
            # Plot data and signals
            plt.figure(figsize=(12,8))
            plt.plot(data['Close'], label='Close Price', alpha=0.5)
            plt.plot(data['SMA1'], label=f'SMA {short_window}-day', alpha=0.75)
            plt.plot(data['SMA2'], label=f'SMA {medium_window}-day', alpha=0.75)
            if long_window:
                plt.plot(data['SMA3'], label=f'SMA {long_window}-day', alpha=0.75)
            
            if strategy == 'Cross between price and SMA 1':
                plt.plot(data[data['Position'] == 1].index, data['SMA1'][data['Position'] == 1], '^', markersize=10, color='g', label='Buy Signal')
                plt.plot(data[data['Position'] == -1].index, data['SMA1'][data['Position'] == -1], 'v', markersize=10, color='r', label='Sell Signal')
            elif strategy == 'Cross between SMA 1 and SMA 2':
                plt.plot(data[data['Position'] == 1].index, data['SMA1'][data['Position'] == 1], '^', markersize=10, color='g', label='Buy Signal')
                plt.plot(data[data['Position'] == -1].index, data['SMA1'][data['Position'] == -1], 'v', markersize=10, color='r', label='Sell Signal')
            elif strategy == 'Cross between SMAs 1, 2 and 3':
                plt.plot(data[data['Position'] == 1].index, data['SMA1'][data['Position'] == 1], '^', markersize=10, color='g', label='Buy Signal')
                plt.plot(data[data['Position'] == -1].index, data['SMA1'][data['Position'] == -1], 'v', markersize=10, color='r', label='Sell Signal')
            
            plt.title(f'{ticker} Trading Strategy Backtest')
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.legend(loc='best')
            plt.grid(True)
            st.pyplot(plt)  # Use Streamlit to display the plot
            plt.close()  # Close the plot to free memory
            
            # Append result for this ticker and strategy
            all_results.append({
                'Ticker': ticker,
                'Strategy': strategy,
                'Total Return (%)': total_return * 100,
                'Annualized Return (%)': annualized_return,
                'Buy-and-Hold Return (%)': buy_and_hold_return,
                'Annualized Buy-and-Hold Return (%)': annualized_buy_and_hold_return,
                'Total-to-Buy-and-Hold Ratio': total_to_buy_and_hold_ratio,
                'Annualized-to-Buy-and-Hold Ratio': annualized_to_buy_and_hold_ratio
            })
        
        except Exception as e:
            st.error(f"An error occurred for ticker {ticker}: {e}")
    
    return all_results
