import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime

def calculate_annualized_return(total_return, days):
    # Convert total return percentage to a decimal for calculation
    total_return_decimal = total_return / 100
    # Annualize the return
    annualized_return = (1 + total_return_decimal) ** (365 / days) - 1
    return annualized_return * 100  # Convert back to percentage

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
            
            # Calculate annualized return
            annualized_return = calculate_annualized_return(total_return * 100, days)
            
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
                'Annualized Return (%)': annualized_return
            })
        
        except Exception as e:
            st.error(f"An error occurred for ticker {ticker}: {e}")
    
    return all_results

# Streamlit app
def main():
    st.title("Trading Strategy Backtest")

    # User inputs
    tickers = st.text_input("Enter Stock Tickers (separated by commas, e.g., AAPL, MSFT):", "AAPL, MSFT").upper().split(',')
    tickers = [ticker.strip() for ticker in tickers]
    start_date = st.date_input("Start Date", pd.to_datetime('2022-01-01'))
    end_date = st.date_input("End Date", pd.to_datetime(datetime.today()))  # Default end date to today
    
    short_window = st.slider("Short Window (days)", min_value=1, max_value=100, value=40)
    medium_window = st.slider("Medium Window (days)", min_value=1, max_value=100, value=100)
    long_window = st.slider("Long Window (days)", min_value=1, max_value=200, value=200)
    
    start_with_position = st.checkbox("Assume starting with a position bought on the start date", value=False)

    if st.button("Run Backtest"):
        if start_date < end_date:
            strategies = [
                'Cross between price and SMA 1',
                'Cross between SMA 1 and SMA 2',
                'Cross between SMAs 1, 2 and 3'
            ]
            
            all_results = []
            for strategy in strategies:
                results = backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, strategy, start_with_position)
                all_results.extend(results)
            
            # Display results as a DataFrame
            results_df = pd.DataFrame(all_results)
            st.write(results_df)
        else:
            st.error("End date must be after the start date.")

if __name__ == "__main__":
    main()
