import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from scipy.optimize import newton
from requests.exceptions import RequestException

def calculate_irr(cash_flows):
    """Calculate the Internal Rate of Return (IRR)"""
    def npv(irr):
        return np.sum(np.array(cash_flows) / (1 + irr) ** np.arange(len(cash_flows)))
    
    try:
        irr = newton(npv, 0.1)
        return irr * 100  # Return IRR as percentage
    except Exception as e:
        st.error(f"Error calculating IRR: {e}")
        return None

def plot_strategy(data, strategy, ticker):
    """Plot the strategy results"""
    plt.figure(figsize=(12, 8))
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

    # Save plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    st.image(buf, use_column_width=True)
    plt.close()

def fetch_data(ticker, start_date, end_date):
    """Fetch historical data with error handling and timeout"""
    try:
        data = yf.download(ticker, start=start_date, end=end_date, timeout=10)
        if data.empty:
            st.warning(f"No data available for ticker {ticker}.")
        return data
    except RequestException as e:
        st.error(f"RequestException for ticker {ticker}: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred while fetching data for ticker {ticker}: {e}")
        return pd.DataFrame()

def backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, strategy, start_with_position):
    """Backtest trading strategies"""
    all_results = []
    for ticker in tickers:
        data = fetch_data(ticker, start_date, end_date)
        if data.empty:
            continue
        
        try:
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
            cash_flows = []
            current_position = 1 if start_with_position else 0
            entry_price = data['Close'].iloc[0] if start_with_position else 0
            
            # Track trades based on signals
            for i in range(1, len(data)):
                if data['Position'].iloc[i] == 1 and current_position == 0:  # Buy signal
                    cash_flows.append(-data['Close'].iloc[i])  # Outflow
                    entry_price = data['Close'].iloc[i]
                    current_position = 1
                elif data['Position'].iloc[i] == -1 and current_position == 1:  # Sell signal
                    cash_flows.append(data['Close'].iloc[i])  # Inflow
                    trade_return = (data['Close'].iloc[i] - entry_price) / entry_price
                    trades.append(trade_return)
                    current_position = 0
            
            # Handle remaining position
            if current_position == 1:
                final_price = data['Close'].iloc[-1]
                cash_flows.append(final_price)  # Inflow
                trade_return = (final_price - entry_price) / entry_price
                trades.append(trade_return)
            
            # Calculate total return from all trades
            total_return = sum(trades)
            
            # Calculate IRR
            irr = calculate_irr(cash_flows)
            
            # Plot data and signals
            plot_strategy(data, strategy, ticker)
            
            # Append result for this ticker and strategy
            all_results.append({
                'Ticker': ticker,
                'Strategy': strategy,
                'Total Return (%)': total_return * 100,
                'IRR (%)': irr if irr is not None else np.nan
            })
        
        except Exception as e:
            st.error(f"An error occurred for ticker {ticker}: {e}")
    
    return all_results

def main():
    st.title("Trading Strategy Backtesting")
    
    tickers = st.text_input("Enter ticker symbols separated by commas (e.g., AAPL,MSFT)").upper().split(',')
    start_date = st.date_input("Start Date", value=pd.to_datetime('2023-01-01'))
    end_date = st.date_input("End Date", value=pd.to_datetime('today'))
    
    strategies = [
        'Cross between price and SMA 1',
        'Cross between SMA 1 and SMA 2',
        'Cross between SMAs 1, 2 and 3'
    ]
    strategy = st.selectbox("Select Strategy", strategies)
    
    short_window = st.slider("Short Window (days)", min_value=5, max_value=50, value=20)
    medium_window = st.slider("Medium Window (days)", min_value=50, max_value=100, value=50)
    long_window = st.slider("Long Window (days)", min_value=100, max_value=200, value=100)
    
    start_with_position = st.checkbox("Assume starting with a position bought on the start date")
    
    if st.button("Run Backtest"):
        if start_date < end_date:
            results = backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, strategy, start_with_position)
            
            if results:
                df_results = pd.DataFrame(results)
                st.write(df_results)
                
                # Analysis of the best strategy
                best_strategy = df_results.loc[df_results['Total Return (%)'].idxmax()]
                best_irr_strategy = df_results.loc[df_results['IRR (%)'].idxmax()]
                
                st.write(f"Best Strategy Based on Total Return: {best_strategy['Strategy']} ({best_strategy['Total Return (%)']:.2f}%)")
                st.write(f"Best Strategy Based on IRR: {best_irr_strategy['Strategy']} ({best_irr_strategy['IRR (%)']:.2f}%)")
            else:
                st.write("No results to display.")
        else:
            st.error("End date must be later than start date.")

if __name__ == "__main__":
    main()
