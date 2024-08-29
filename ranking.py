import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime

def calculate_annualized_return(total_return, days):
    total_return_decimal = total_return / 100
    annualized_return = (1 + total_return_decimal) ** (365 / days) - 1
    return annualized_return * 100

def calculate_buy_and_hold_return(start_price, end_price):
    return (end_price - start_price) / start_price * 100

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
            if not quick_analysis:
                st.pyplot(plt)  # Use Streamlit to display the plot
            plt.close()  # Close the plot to free memory
            
            # Append result for this ticker and strategy
            all_results.append({
                'Ticker': ticker,
                'Strategy': strategy,
                'Total Return (%)': total_return * 100,
                'Annualized Return (%)': annualized_return,
                'Buy-and-Hold Return (%)': buy_and_hold_return
            })
        
        except Exception as e:
            st.error(f"An error occurred for ticker {ticker}: {e}")
    
    return all_results

def quick_analysis(tickers, start_date, end_date):
    all_results = []
    
    for ticker in tickers:
        try:
            # Fetch historical data
            data = yf.download(ticker, start=start_date, end=end_date)
            if data.empty:
                st.error(f"No data fetched for ticker {ticker}.")
                continue
            
            start_price = data['Close'].iloc[0]
            end_price = data['Close'].iloc[-1]
            buy_and_hold_return = calculate_buy_and_hold_return(start_price, end_price)
            days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
            if days == 0:
                days = 1  # Avoid division by zero
            
            # Analyze SMA cross strategies
            for short_window in range(1, 101):
                for medium_window in range(short_window + 1, 101):
                    # Calculate SMAs
                    data['SMA1'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
                    data['SMA2'] = data['Close'].rolling(window=medium_window, min_periods=1).mean()
                    
                    # Cross between price and SMA1
                    data['Signal'] = 0
                    data['Signal'][short_window:] = np.where(data['Close'][short_window:] > data['SMA1'][short_window:], 1, 0)
                    data['Position'] = data['Signal'].diff()
                    
                    # Track trades
                    trades = []
                    current_position = 1
                    entry_price = data['Close'].iloc[0]
                    
                    for i in range(1, len(data)):
                        if data['Position'].iloc[i] == 1 and current_position == 0:
                            entry_price = data['Close'].iloc[i]
                            current_position = 1
                        elif data['Position'].iloc[i] == -1 and current_position == 1:
                            exit_price = data['Close'].iloc[i]
                            trade_return = (exit_price - entry_price) / entry_price
                            trades.append(trade_return)
                            current_position = 0
                    
                    if current_position == 1:
                        final_price = data['Close'].iloc[-1]
                        trade_return = (final_price - entry_price) / entry_price
                        trades.append(trade_return)
                    
                    total_return = sum(trades)
                    annualized_return = calculate_annualized_return(total_return * 100, days)
                    
                    all_results.append({
                        'Ticker': ticker,
                        'Strategy': f'Price and SMA1 ({short_window} days)',
                        'Total Return (%)': total_return * 100,
                        'Annualized Return (%)': annualized_return,
                        'Buy-and-Hold Return (%)': buy_and_hold_return
                    })
                    
                    # Cross between SMA1 and SMA2
                    data['Signal'] = 0
                    data['Signal'][medium_window:] = np.where(data['SMA1'][medium_window:] > data['SMA2'][medium_window:], 1, 0)
                    data['Position'] = data['Signal'].diff()
                    
                    trades = []
                    current_position = 1
                    entry_price = data['Close'].iloc[0]
                    
                    for i in range(1, len(data)):
                        if data['Position'].iloc[i] == 1 and current_position == 0:
                            entry_price = data['Close'].iloc[i]
                            current_position = 1
                        elif data['Position'].iloc[i] == -1 and current_position == 1:
                            exit_price = data['Close'].iloc[i]
                            trade_return = (exit_price - entry_price) / entry_price
                            trades.append(trade_return)
                            current_position = 0
                    
                    if current_position == 1:
                        final_price = data['Close'].iloc[-1]
                        trade_return = (final_price - entry_price) / entry_price
                        trades.append(trade_return)
                    
                    total_return = sum(trades)
                    annualized_return = calculate_annualized_return(total_return * 100, days)
                    
                    all_results.append({
                        'Ticker': ticker,
                        'Strategy': f'SMA1 and SMA2 ({short_window}/{medium_window} days)',
                        'Total Return (%)': total_return * 100,
                        'Annualized Return (%)': annualized_return,
                        'Buy-and-Hold Return (%)': buy_and_hold_return
                    })
                    
            # Compare with Buy-and-Hold strategy
            for short_window in range(1, 101):
                for medium_window in range(short_window + 1, 101):
                    for long_window in range(medium_window + 1, 101):
                        data['SMA1'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
                        data['SMA2'] = data['Close'].rolling(window=medium_window, min_periods=1).mean()
                        data['SMA3'] = data['Close'].rolling(window=long_window, min_periods=1).mean()
                        
                        # Cross between SMA1, SMA2, and SMA3
                        data['Signal'] = 0
                        bullish_alignment = (data['SMA1'] > data['SMA2']) & (data['SMA2'] > data['SMA3'])
                        bearish_alignment = (data['SMA1'] < data['SMA2']) & (data['SMA2'] < data['SMA3'])
                        data['Signal'] = np.where(bullish_alignment, 1, 0)
                        data['Signal'] = np.where(bearish_alignment, -1, data['Signal'])
                        data['Position'] = data['Signal'].diff()
                        
                        trades = []
                        current_position = 1
                        entry_price = data['Close'].iloc[0]
                        
                        for i in range(1, len(data)):
                            if data['Position'].iloc[i] == 1 and current_position == 0:
                                entry_price = data['Close'].iloc[i]
                                current_position = 1
                            elif data['Position'].iloc[i] == -1 and current_position == 1:
                                exit_price = data['Close'].iloc[i]
                                trade_return = (exit_price - entry_price) / entry_price
                                trades.append(trade_return)
                                current_position = 0
                        
                        if current_position == 1:
                            final_price = data['Close'].iloc[-1]
                            trade_return = (final_price - entry_price) / entry_price
                            trades.append(trade_return)
                        
                        total_return = sum(trades)
                        annualized_return = calculate_annualized_return(total_return * 100, days)
                        
                        all_results.append({
                            'Ticker': ticker,
                            'Strategy': f'SMA1, SMA2, and SMA3 ({short_window}/{medium_window}/{long_window} days)',
                            'Total Return (%)': total_return * 100,
                            'Annualized Return (%)': annualized_return,
                            'Buy-and-Hold Return (%)': buy_and_hold_return
                        })
        
        except Exception as e:
            st.error(f"An error occurred for ticker {ticker}: {e}")
    
    return all_results

def main():
    st.title("Backtesting Trading Strategies")

    # Streamlit inputs
    tickers_input = st.text_input("Enter Tickers (comma-separated):")
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(',')] if tickers_input else []

    start_date = st.date_input("Start Date", datetime(2023, 1, 1))
    end_date = st.date_input("End Date", datetime.today())

    quick_analysis_option = st.checkbox("Análisis rápido de rendimientos")
    start_with_position = st.checkbox("Asumir posición comprada en la fecha de inicio")
    
    # Default end date to today if not specified
    if not end_date:
        end_date = datetime.today()

    if quick_analysis_option:
        st.write("Running quick performance analysis...")
        results = quick_analysis(tickers, start_date, end_date)
    else:
        strategy = st.selectbox("Select Strategy", [
            "Cross between price and SMA 1",
            "Cross between SMA 1 and SMA 2",
            "Cross between SMAs 1, 2 and 3"
        ])
        short_window = st.slider("Short Window (SMA1)", 1, 100, 20)
        medium_window = st.slider("Medium Window (SMA2)", 1, 100, 50)
        long_window = st.slider("Long Window (SMA3)", 1, 100, 100)
        
        if st.button("Run Backtest"):
            st.write("Running backtest...")
            results = backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, strategy, start_with_position)
    
    if 'results' in locals():
        results_df = pd.DataFrame(results)
        st.write(results_df)

if __name__ == "__main__":
    main()
