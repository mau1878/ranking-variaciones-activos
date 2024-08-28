import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(page_title="Stock Price Variations", layout="wide")

# Input fields
st.title("Stock Price Variation Analyzer")
ticker = st.text_input("Enter the ticker symbol:", "AAPL")
start_date = st.date_input("Start date:", value=pd.to_datetime("1970-01-01"))
end_date = st.date_input("End date:", value=pd.to_datetime("today"))

# Frequency selection
frequency = st.selectbox("Select frequency:", ["Daily", "Weekly", "Monthly"])

# Fetch data
if ticker:
    df = yf.download(ticker, start=start_date, end=end_date)

    if not df.empty:
        # Resample data based on selected frequency
        if frequency == "Daily":
            df_resampled = df
        elif frequency == "Weekly":
            df_resampled = df.resample('W').last()
        elif frequency == "Monthly":
            df_resampled = df.resample('M').last()

        # Calculate price variations
        df_resampled['Price Variation'] = df_resampled['Adj Close'].pct_change()
        df_resampled['Next Day Variation'] = df_resampled['Price Variation'].shift(-1)
        df_resampled.dropna(inplace=True)

        # Get top 30 most positive and negative variations
        top_positive = df_resampled.nlargest(30, 'Price Variation')
        top_negative = df_resampled.nsmallest(30, 'Price Variation')

        # Style function for color-coding the variations
        def color_variation(val):
            color = 'green' if val > 0 else 'red'
            return f'background-color: {color}; opacity: {min(0.5 + abs(val), 1)}'

        # Display tables
        st.subheader(f"Top 30 Positive Price Variations for {ticker} ({frequency})")
        st.write(top_positive[['Price Variation', 'Next Day Variation']].style.applymap(color_variation))

        st.subheader(f"Top 30 Negative Price Variations for {ticker} ({frequency})")
        st.write(top_negative[['Price Variation', 'Next Day Variation']].style.applymap(color_variation))

    else:
        st.error("No data found for the specified ticker and date range.")
else:
    st.warning("Please enter a ticker symbol.")
