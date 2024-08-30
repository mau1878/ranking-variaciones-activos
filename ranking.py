import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from io import BytesIO
from datetime import datetime, timedelta

# Función para calcular el rendimiento de compra y mantenimiento
def calculate_buy_and_hold_return(start_price, end_price):
    return (end_price - start_price) / start_price

# Función para calcular el rendimiento anualizado
def calculate_annualized_return(total_return_percent, days):
    if days == 0:
        return np.nan  # Evitar división por cero
    return ((1 + total_return_percent / 100) ** (365 / days) - 1) * 100

# Función para calcular el rendimiento anualizado de compra y mantenimiento
def calculate_annualized_buy_and_hold_return(start_price, end_price, days):
    buy_and_hold_return = calculate_buy_and_hold_return(start_price, end_price)
    return calculate_annualized_return(buy_and_hold_return * 100, days)

def backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, start_with_position, buffer_days=200):
    all_results = []
    
    for ticker in tickers:
        try:
            # Establecer la fecha de inicio extendida para el cálculo de SMAs
            extended_start_date = (pd.to_datetime(start_date) - timedelta(days=buffer_days)).strftime('%Y-%m-%d')
            
            # Obtener datos históricos
            data = yf.download(ticker, start=extended_start_date, end=end_date)
            if data.empty:
                st.error(f"No se obtuvieron datos para el ticker {ticker}.")
                continue
            
            # Filtrar datos para el período especificado por el usuario
            data_filtered = data.loc[start_date:end_date]
            if data_filtered.empty:
                st.error(f"No se obtuvieron datos para el período especificado para el ticker {ticker}.")
                continue
            
            # Calcular medias móviles sobre los datos extendidos
            data['SMA1'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
            data['SMA2'] = data['Close'].rolling(window=medium_window, min_periods=1).mean()
            data['SMA3'] = data['Close'].rolling(window=long_window, min_periods=1).mean()
            
            # Rendimiento de Compra y Mantenimiento
            start_price = data_filtered['Close'].iloc[0]
            end_price = data_filtered['Close'].iloc[-1]
            buy_and_hold_return = calculate_buy_and_hold_return(start_price, end_price)
            
            strategies = [
                ('Cruce entre el precio y SMA 1', data_filtered['Close'] > data['SMA1']),
                ('Cruce entre SMA 1 y SMA 2', data['SMA1'] > data['SMA2']),
                ('Cruce entre SMA 1, 2 y 3', (data['SMA1'] > data['SMA2']) & (data['SMA2'] > data['SMA3']))
            ]
            
            for strategy_name, signal_condition in strategies:
                # Generar señales
                data_filtered['Signal'] = 0
                data_filtered['Signal'][short_window:] = np.where(signal_condition[short_window:], 1, 0)
                data_filtered['Position'] = data_filtered['Signal'].diff()
                
                # Inicializar variables para seguimiento de operaciones
                trades = []
                current_position = 1 if start_with_position else 0
                entry_price = data_filtered['Close'].iloc[0] if start_with_position else 0
                
                # Rastrear operaciones basadas en señales
                for i in range(1, len(data_filtered)):
                    if data_filtered['Position'].iloc[i] == 1 and current_position == 0:  # Señal de compra
                        entry_price = data_filtered['Close'].iloc[i]
                        current_position = 1
                    elif data_filtered['Position'].iloc[i] == -1 and current_position == 1:  # Señal de venta
                        exit_price = data_filtered['Close'].iloc[i]
                        trade_return = (exit_price - entry_price) / entry_price
                        trades.append(trade_return)
                        current_position = 0
                
                # Manejar posición restante
                if current_position == 1:
                    final_price = data_filtered['Close'].iloc[-1]
                    trade_return = (final_price - entry_price) / entry_price
                    trades.append(trade_return)
                
                # Calcular rendimiento total de todas las operaciones
                total_return = sum(trades)
                
                # Calcular el número de días en el período de prueba
                days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
                if days <= 0:
                    days = 1  # Evitar división por cero
                
                # Calcular rendimientos anualizados
                annualized_return = calculate_annualized_return(total_return * 100, days)
                annualized_buy_and_hold_return = calculate_annualized_buy_and_hold_return(start_price, end_price, days)
                
                # Calcular ratios
                if buy_and_hold_return != 0:
                    total_to_buy_and_hold_ratio = total_return / buy_and_hold_return
                else:
                    total_to_buy_and_hold_ratio = np.nan  # Manejar división por cero

                if annualized_buy_and_hold_return != 0:
                    annualized_to_buy_and_hold_ratio = annualized_return / annualized_buy_and_hold_return
                else:
                    annualized_to_buy_and_hold_ratio = np.nan  # Manejar división por cero
                
                # Agregar resultado para este ticker y estrategia
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
                
                # Graficar
                plt.figure(figsize=(10, 6))
                plt.plot(data.index, data['Close'], label='Precio', alpha=0.7)
                plt.plot(data.index, data['SMA1'], label='SMA1', alpha=0.7)
                plt.plot(data.index, data['SMA2'], label='SMA2', alpha=0.7)
                plt.plot(data.index, data['SMA3'], label='SMA3', alpha=0.7)
                
                # Ajustar el rango de fechas en el gráfico para que comience desde el inicio del período especificado
                plt.xlim(start_date, end_date)
                
                # Señales de compra y venta
                buy_signals = data_filtered[data_filtered['Position'] == 1]
                sell_signals = data_filtered[data_filtered['Position'] == -1]
                plt.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='g', label='Señal de Compra', s=100)
                plt.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='r', label='Señal de Venta', s=100)
                
                plt.title(f'{ticker} - {strategy_name}')
                plt.xlabel('Fecha')
                plt.ylabel('Precio')
                plt.legend()
                plt.grid(True)
                
                # Guardar el gráfico en un objeto BytesIO
                buf = BytesIO()
                plt.savefig(buf, format="png")
                buf.seek(0)
                st.image(buf, caption=f"Gráfico de {ticker} - {strategy_name}")
                plt.close()
        
        except Exception as e:
            st.error(f"Ocurrió un error para el ticker {ticker}: {e}")
    
    return all_results

# Ejemplo de uso
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
    
    if st.button("Ejecutar Estrategia"):
        results = backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, start_with_position)
        if results:
            df_results = pd.DataFrame(results)
            st.write("Resultados de la Estrategia de Trading:")
            st.dataframe(df_results)
