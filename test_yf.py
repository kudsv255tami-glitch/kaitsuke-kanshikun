import yfinance as yf
import time

def test_fetch(ticker):
    print(f"Testing {ticker}...")
    try:
        s = yf.Ticker(ticker)
        h = s.history(period="1d")
        if not h.empty:
            print(f"Success! Price: {h['Close'].iloc[-1]}")
            print(f"Info: {s.info.get('shortName')}")
        else:
            print("Failed: No data found.")
    except Exception as e:
        print(f"Error: {e}")

test_fetch("7203.T")
test_fetch("AAPL")
