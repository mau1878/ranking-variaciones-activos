import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

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
                st.error(f"No se obtuvieron datos para el ticker {ticker}.")
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
                ('Cruz entre el precio y SMA 1', data['Close'] > data['SMA1']),
                ('Cruz entre SMA 1 y SMA 2', data['SMA1'] > data['SMA2']),
                ('Cruz entre SMA 1, 2 y 3', (data['SMA1'] > data['SMA2']) & (data['SMA2'] > data['SMA3']))
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
                    'Estrategia': strategy_name,
                    'Rendimiento Total (%)': total_return * 100,
                    'Rendimiento Anualizado (%)': annualized_return,
                    'Rendimiento de Compra y Mantenimiento (%)': buy_and_hold_return * 100,
                    'Rendimiento Anualizado de Compra y Mantenimiento (%)': annualized_buy_and_hold_return,
                    'Ratio Total-a-Compra y Mantenimiento': total_to_buy_and_hold_ratio,
                    'Ratio Anualizado-a-Compra y Mantenimiento': annualized_to_buy_and_hold_ratio
                })
                
                # Plotting with Plotly
                try:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Precio'))
                    fig.add_trace(go.Scatter(x=data.index, y=data['SMA1'], mode='lines', name='SMA1', line=dict(dash='dash')))
                    fig.add_trace(go.Scatter(x=data.index, y=data['SMA2'], mode='lines', name='SMA2', line=dict(dash='dash')))
                    fig.add_trace(go.Scatter(x=data.index, y=data['SMA3'], mode='lines', name='SMA3', line=dict(dash='dash')))
                    
                    # Buy and sell signals
                    buy_signals = data[data['Position'] == 1]
                    sell_signals = data[data['Position'] == -1]
                    fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='Señal de Compra', marker=dict(color='green', symbol='triangle-up', size=10)))
                    fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'], mode='markers', name='Señal de Venta', marker=dict(color='red', symbol='triangle-down', size=10)))
                    
                    fig.update_layout(title=f'{ticker} - {strategy_name}',
                                      xaxis_title='Fecha',
                                      yaxis_title='Precio',
                                      legend_title='Leyenda',
                                      template='plotly_dark')
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as plot_error:
                    st.error(f"Error al generar el gráfico para el ticker {ticker}: {plot_error}")
        
        except Exception as e:
            st.error(f"Ocurrió un error para el ticker {ticker}: {e}")
    
    return all_results

# Example usage
if __name__ == "__main__":
    st.title("Prueba de Estrategia de Trading")
    
    tickers = st.text_input("Ingrese tickers (separados por comas):", "AAPL, MSFT").split(',')
    tickers = [ticker.strip().upper() for ticker in tickers]
    start_date = st.date_input("Fecha de Inicio", pd.to_datetime('2023-01-01'))
    end_date = st.date_input("Fecha de Fin", datetime.today().date())
    short_window = st.slider("Ventana Corta", 1, 60, 20)
    medium_window = st.slider("Ventana Media", 1, 100, 50)
    long_window = st.slider("Ventana Larga", 1, 60, 200)
    start_with_position = st.checkbox("Empezar con Posición Inicial", value=False)
    
    if st.button("Ejecutar Prueba"):
        results = backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, start_with_position)
        results_df = pd.DataFrame(results)
        st.write(results_df)
        st.write("Resultados calculados con éxito.")
