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
    
    # Convert dates to Timestamp for consistent comparison
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)
    
    strategy_explanations = {
        'Cruce entre el precio y SMA 1': 'Señal de compra cuando el precio de cierre está por encima de la SMA1 y señal de venta cuando está por debajo.',
        'Cruce entre SMA 1 y SMA 2': 'Señal de compra cuando la SMA1 está por encima de la SMA2 y señal de venta cuando está por debajo.',
        'Cruce entre SMA 1, 2 y 3': 'Señal de compra cuando la SMA1 está por encima de la SMA2 y la SMA2 está por encima de la SMA3. Señal de venta cuando estas condiciones no se cumplen.'
    }
    
    for ticker in tickers:
        try:
            # Establecer la fecha de inicio extendida para el cálculo de SMAs
            extended_start_date = (start_date - timedelta(days=buffer_days)).strftime('%Y-%m-%d')
            
            # Obtener datos históricos
            data = yf.download(ticker, start=extended_start_date, end=end_date + timedelta(days=1))
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
            
            # Filtrar SMAs para que coincidan con el período especificado
            data_filtered['SMA1'] = data['SMA1'].loc[start_date:end_date]
            data_filtered['SMA2'] = data['SMA2'].loc[start_date:end_date]
            data_filtered['SMA3'] = data['SMA3'].loc[start_date:end_date]
            
            # Rendimiento de Compra y Mantenimiento
            start_price = data_filtered['Close'].iloc[0]
            end_price = data_filtered['Close'].iloc[-1]
            buy_and_hold_return = calculate_buy_and_hold_return(start_price, end_price)
            
            strategies = [
                ('Cruce entre el precio y SMA 1', data_filtered['Close'] > data_filtered['SMA1']),
                ('Cruce entre SMA 1 y SMA 2', data_filtered['SMA1'] > data_filtered['SMA2']),
                ('Cruce entre SMA 1, 2 y 3', (data_filtered['SMA1'] > data_filtered['SMA2']) & (data_filtered['SMA2'] > data_filtered['SMA3']))
            ]
            
            for strategy_name, signal_condition in strategies:
                # Generar señales
                data_filtered['Signal'] = 0
                data_filtered.loc[signal_condition, 'Signal'] = 1
                data_filtered['Position'] = data_filtered['Signal'].diff()
                
                # Inicializar variables para seguimiento de operaciones
                trades = []
                current_position = 1 if start_with_position else 0
                entry_price = data_filtered['Close'].iloc[0] if start_with_position else 0
                
                # Rastrear operaciones basadas en señales
                for i in range(1, len(data_filtered)):
                    if data_filtered.index[i] < start_date or data_filtered.index[i] > end_date:
                        continue
                    
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
                days = (end_date - start_date).days
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
                plt.plot(data_filtered.index, data_filtered['Close'], label='Precio', alpha=0.7)
                plt.plot(data_filtered.index, data_filtered['SMA1'], label='SMA1', alpha=0.7)
                plt.plot(data_filtered.index, data_filtered['SMA2'], label='SMA2', alpha=0.7)
                plt.plot(data_filtered.index, data_filtered['SMA3'], label='SMA3', alpha=0.7)
                
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
                
                # Mostrar explicación de la estrategia
                explanation = strategy_explanations.get(strategy_name, "No hay explicación disponible.")
                st.write(f"### Explicación de la Estrategia: {strategy_name}")
                st.write(explanation)
        
        except Exception as e:
            st.error(f"Error al procesar el ticker {ticker}: {e}")
    
    # Crear DataFrame de resultados
    results_df = pd.DataFrame(all_results)
    
    # Mostrar tabla de resultados
    st.write("### Resultados de la Estrategia")
    st.dataframe(results_df)

# Configuración de la aplicación de Streamlit
st.title("Backtest de Estrategias de Inversión")
st.write("Selecciona los tickers, fechas y parámetros para el backtest de las estrategias de inversión.")

# Entrada de usuarios
tickers_input = st.text_input("Ingresa los tickers separados por comas", "MSFT, AAPL, TSLA")
tickers = [ticker.strip().upper() for ticker in tickers_input.split(',')]

start_date = st.date_input("Fecha de inicio", value=datetime(2023, 1, 1), min_value=datetime(1980, 1, 1), max_value=datetime(2024, 8, 31))
end_date = st.date_input("Fecha de fin", value=datetime.today())
short_window = st.slider("Periodo de SMA 1", min_value=1, max_value=50, value=20)
medium_window = st.slider("Periodo de SMA 2", min_value=1, max_value=50, value=50)
long_window = st.slider("Periodo de SMA 3", min_value=1, max_value=50, value=200)
start_with_position = st.checkbox("Empezar con posición", value=True)

if st.button("Ejecutar Backtest"):
    backtest_strategy(tickers, start_date, end_date, short_window, medium_window, long_window, start_with_position)
