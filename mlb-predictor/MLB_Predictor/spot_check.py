import yfinance as yf

h = yf.Ticker('BTC-USD').history(period='1d')
print('BTC spot:', h['Close'].iloc[-1])

h2 = yf.Ticker('ETH-USD').history(period='1d')
print('ETH spot:', h2['Close'].iloc[-1])
#3
