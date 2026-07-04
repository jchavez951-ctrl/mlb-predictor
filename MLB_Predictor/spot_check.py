import streamlit as st
import yfinance as yf

st.title("⚾ MLB Predictor Workspace")
st.write("Your Streamlit environment is fully connected and ready!")

try:
    ticker_data = yf.Ticker('BTC-USD').history(period='1d')
    latest_price = ticker_data['Close'].iloc[-1]
    st.metric(label="Live Test Feed (BTC-USD)", value=f"${latest_price:,.2f}")
    st.success("Data download link is operational!")
except Exception as e:
    st.error(f"Could not connect to external data feed: {e}")mport streamlit as st
import yfinance as yf

st.title("⚾ MLB Predictor Workspace")
st.write("Your Streamlit environment is fully connected and ready!")

try:
    ticker_data = yf.Ticker('BTC-USD').history(period='1d')
    latest_price = ticker_data['Close'].iloc[-1]
    st.metric(label="Live Test Feed (BTC-USD)", value=f"${latest_price:,.2f}")
    st.success("Data download link is operational!")
except Exception as e:
    st.error(f"Could not connect to external data feed:)

h = yf.Ticker('BTC-USD').history(period='1d')
print('BTC spot:', h['Close'].iloc[-1])

h2 = yf.Ticker('ETH-USD').history(period='1d')
print('ETH spot:', h2['Close'].iloc[-1])
#3
