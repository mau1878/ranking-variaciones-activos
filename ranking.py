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

# Font size and table width settings
font_size = st.slider("Select font size for the table:", min_value=10, max_value=30, value=14)
table_width = st.slider("Select table width (in pixels):", min_value=400, max_value=1200, value=800)

# Checkbox to apply CCL de YPF
apply_ccl = st.checkbox("Aplicar CCL de YPF")

def fetch_and_adjust(ticker, start, end):
    data = yf.download(ticker, start=start, end=end)
    # Forward-fill to handle missing values
    data.ffill(inplace=True)
    return data

def fetch_ypf_data(ticker_ypf_ba, ticker_ypf, start, end):
    df_ypf_ba = fetch_and_adjust(ticker_ypf_ba, start=start, end=end)
    df_ypf = fetch_and_adjust(ticker_ypf, start=start, end=end)

    # Backward-fill if the first values are missing
    df_ypf_ba.bfill(inplace=True)
    df_ypf.bfill(inplace=True)

    return df_ypf_ba, df_ypf

# Fetch data
if ticker:
    df = fetch_and_adjust(ticker, start=start_date, end=end_date)

    if not df.empty:
        if apply_ccl:
            # Fetch YPF.BA and YPF data and adjust
            df_ypf_ba, df_ypf = fetch_ypf_data("YPF.BA", "YPF", start_date, end_date)

            if not df_ypf_ba.empty and not df_ypf.empty:
                # Calculate CCL de YPF ratio
                df['CCL de YPF'] = df_ypf_ba['Adj Close'] / df_ypf['Adj Close']

                # Avoid dividing by zero or NaN
                df['CCL de YPF'].replace([np.inf, -np.inf], np.nan, inplace=True)
                df.dropna(subset=['CCL de YPF'], inplace=True)

                # Adjust ticker data by dividing by CCL ratio
                df['Adj Close'] = df['Adj Close'] / df['CCL de YPF']
            else:
                st.warning("Data for YPF.BA or YPF is missing. CCL de YPF ratio could not be applied.")
        
        # Resample data based on selected frequency
        if frequency == "Daily":
            df_resampled = df
        elif frequency == "Weekly":
            df_resampled = df.resample('W').last()
        elif frequency == "Monthly":
            df_resampled = df.resample('M').last()

        # Calculate price variations with two decimal points
        df_resampled['Price Variation (%)'] = (df_resampled['Adj Close'].pct_change() * 100).round(2)
        df_resampled['Next Day Variation (%)'] = df_resampled['Price Variation (%)'].shift(-1).round(2)
        df_resampled.dropna(inplace=True)

        # Format date to remove hour
        df_resampled.index = df_resampled.index.strftime('%Y-%m-%d')

        # Get top 30 most positive and negative variations
        top_positive = df_resampled.nlargest(30, 'Price Variation (%)')
        top_negative = df_resampled.nsmallest(30, 'Price Variation (%)')

        # Style function for color-coding the variations
        def color_variation(val):
            color = 'green' if val > 0 else 'red'
            return f'background-color: {color}; opacity: {min(0.5 + abs(val/100), 1)}'

        # CSS for custom font size and table width
        st.markdown(f"""
            <style>
            .dataframe {{
                font-size: {font_size}px !important;
                width: {table_width}px !important;
            }}
            </style>
            """, unsafe_allow_html=True)

        # Display tables
        if not top_positive.empty:
            st.subheader(f"Top 30 Positive Price Variations for {ticker} ({frequency})")
            st.write(top_positive[['Price Variation (%)', 'Next Day Variation (%)']]
                     .style.applymap(color_variation)
                     .set_table_styles([{'selector': '', 'props': [('width', f'{table_width}px')]}]), unsafe_allow_html=True)

        if not top_negative.empty:
            st.subheader(f"Top 30 Negative Price Variations for {ticker} ({frequency})")
            st.write(top_negative[['Price Variation (%)', 'Next Day Variation (%)']]
                     .style.applymap(color_variation)
                     .set_table_styles([{'selector': '', 'props': [('width', f'{table_width}px')]}]), unsafe_allow_html=True)

    else:
        st.error("No data found for the specified ticker and date range.")
else:
    st.warning("Please enter a ticker symbol.")
