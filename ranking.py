import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

def backtest_strategy(ticker, start_date, end_date, short_window, medium_window, long_window, strategy):
    try:
        # Fetch historical data
        data = yf.download(ticker, start=start_date, end=end_date)
        if data.empty:
            st.error("No data fetched for the given ticker.")
            return
        
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
            data['Signal'] = np.where((data['SMA1'] > data['SMA2']) & (data['SMA2'] > data['SMA3']), 1, 0)
            data['Position'] = data['Signal'].diff()
        
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
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Streamlit app
def main():
    st.title("Trading Strategy Backtest")

    # User inputs
    ticker = st.text_input("Enter Stock Ticker (e.g., AAPL):", "AAPL").upper()
    start_date = st.date_input("Start Date", pd.to_datetime('2022-01-01'))
    end_date = st.date_input("End Date", pd.to_datetime('2023-01-01'))
    
    short_window = st.slider("Short Window (days)", min_value=1, max_value=100, value=40)
    medium_window = st.slider("Medium Window (days)", min_value=1, max_value=100, value=100)
    long_window = st.slider("Long Window (days)", min_value=1, max_value=200, value=200)
    
    strategy = st.selectbox("Choose Strategy", [
        'Cross between price and SMA 1',
        'Cross between SMA 1 and SMA 2',
        'Cross between SMAs 1, 2 and 3'
    ])

    if st.button("Run Backtest"):
        if start_date < end_date:
            backtest_strategy(ticker, start_date, end_date, short_window, medium_window, long_window, strategy)
        else:
            st.error("End date must be after start date.")

if __name__ == "__main__":
    main()
