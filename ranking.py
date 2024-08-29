import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from io import BytesIO

# Function to calculate buy-and-hold return
def calculate_buy_and_hold_return(start_price, end_price):
    return (end_price - start_price) / start_price

# Function to calculate annualized return
def calculate_annualized_return(total_return_percent, days):
    return ((1 + total_return_percent / 100) ** (365 / days) - 1) * 100

# Function to calculate annualized buy-and-hold return
def calculate_annualized_buy_and_hold_return(start_price, end_price, days):
    buy_and_hold_return = calculate_buy_and_hold_return(start_price, end_price)
    return calculate_annualized_return(buy_and_hold_return * 100, days)

def backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, start_with_position):
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
            
            strategies = [
                ('Cross between price and SMA 1', data['Close'] > data['SMA1']),
                ('Cross between SMA 1 and SMA 2', data['SMA1'] > data['SMA2']),
                ('Cross between SMAs 1, 2 and 3', (data['SMA1'] > data['SMA2']) & (data['SMA2'] > data['SMA3']))
            ]
            
            for strategy_name, signal_condition in strategies:
                # Generate signals
                data['Signal'] = 0
                data['Signal'][short_window:] = np.where(signal_condition[short_window:], 1, 0)
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
                    annualized_to_buy_and_hold_ratio = annualized_return / annualized_buy_and_hold_return
                else:
                    annualized_to_buy_and_hold_ratio = np.nan  # Handle division by zero
                
                # Append result for this ticker and strategy
                all_results.append({
                    'Ticker': ticker,
                    'Strategy': strategy_name,
                    'Total Return (%)': total_return * 100,
                    'Annualized Return (%)': annualized_return,
                    'Buy-and-Hold Return (%)': buy_and_hold_return,
                    'Annualized Buy-and-Hold Return (%)': annualized_buy_and_hold_return,
                    'Total-to-Buy-and-Hold Ratio': total_to_buy_and_hold_ratio,
                    'Annualized-to-Buy-and-Hold Ratio': annualized_to_buy_and_hold_ratio
                })
                
                # Plotting
                plt.figure(figsize=(10, 6))
                plt.plot(data.index, data['Close'], label='Price')
                plt.plot(data.index, data['SMA1'], label='SMA1', alpha=0.7)
                plt.plot(data.index, data['SMA2'], label='SMA2', alpha=0.7)
                plt.plot(data.index, data['SMA3'], label='SMA3', alpha=0.7)
                plt.title(f'{ticker} - {strategy_name}')
                plt.xlabel('Date')
                plt.ylabel('Price')
                plt.legend()
                plt.grid(True)
                
                # Save the plot to a BytesIO object
                buf = BytesIO()
                plt.savefig(buf, format="png")
                buf.seek(0)
                st.image(buf, caption=f"{ticker} - {strategy_name} Plot")
                plt.close()
        
        except Exception as e:
            st.error(f"An error occurred for ticker {ticker}: {e}")
    
    return all_results

# Example usage
if __name__ == "__main__":
    st.title("Trading Strategy Backtest")
    
    tickers = st.text_input("Enter tickers (comma-separated):", "AAPL, MSFT").split(',')
    tickers = [ticker.strip().upper() for ticker in tickers]
    start_date = st.date_input("Start Date", pd.to_datetime('2023-01-01'))
    end_date = st.date_input("End Date", pd.to_datetime('2024-01-01'))
    short_window = st.slider("Short Window", 1, 60, 20)
    medium_window = st.slider("Medium Window", 1, 60, 50)
    long_window = st.slider("Long Window", 1, 60, 200)
    start_with_position = st.checkbox("Start with Initial Position", value=False)
    
    if st.button("Run Backtest"):
        results = backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, start_with_position)
        results_df = pd.DataFrame(results)
        st.write(results_df)
        st.write("Results successfully calculated.")
