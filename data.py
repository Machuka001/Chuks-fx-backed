# data.py
import yfinance as yf
import pandas as pd

# Yahoo symbol for Gold vs USD is "XAUUSD=X"
def fetch_history(symbol: str = "XAUUSD=X", interval: str = "1h", period_days: int = 180) -> pd.DataFrame:
    period_map = {
        "1h": "730d" if period_days > 730 else f"{period_days}d",
        "30m": f"{min(period_days, 60)}d",
        "15m": f"{min(period_days, 60)}d",
        "1d": f"{min(period_days, 3650)}d"
    }
    period = period_map.get(interval, f"{period_days}d")
    df = yf.download(symbol, interval=interval, period=period, progress=False)
    if df is None or df.empty:
        raise ValueError("No data returned from Yahoo. Try a different interval or symbol.")
    df = df.rename(columns=str.title)  # Open,High,Low,Close,Adj Close,Volume
    return df
