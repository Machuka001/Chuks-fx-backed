# tv_ai_engine.py
# Pulls historical XAUUSD, computes indicators, SMC heuristics, and returns a signal + analysis
import pandas as pd
import numpy as np
import yfinance as yf
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime, timedelta

# --- Helper indicators / features ---
def fetch_history(symbol="XAUUSD=X", interval="1h", period_days=365):
    # yfinance period arg examples: "365d", "730d"
    period = f"{period_days}d"
    df = yf.download(symbol, interval=interval, period=period, progress=False)
    if df is None or df.empty:
        raise ValueError("No data returned from yfinance; try a different period or symbol.")
    df = df.rename(columns=str.title)  # Open, High, Low, Close, Adj Close, Volume
    df = df[['Open','High','Low','Close','Volume']].dropna()
    df.index = pd.to_datetime(df.index)
    return df

def compute_indicators(df):
    d = df.copy()
    d['ema20'] = EMAIndicator(d['Close'], window=20).ema_indicator()
    d['ema50'] = EMAIndicator(d['Close'], window=50).ema_indicator()
    d['ema200'] = EMAIndicator(d['Close'], window=200).ema_indicator()
    macd = MACD(d['Close'])
    d['macd'] = macd.macd()
    d['macd_sig'] = macd.macd_signal()
    d['rsi14'] = RSIIndicator(d['Close'], window=14).rsi()
    d['atr14'] = AverageTrueRange(high=d['High'], low=d['Low'], close=d['Close'], window=14).average_true_range()
    # Momentum returns
    d['ret1'] = d['Close'].pct_change()
    d = d.dropna()
    return d

# --- Heuristic SMC detectors (simple versions to start) ---
def detect_order_blocks(df, lookback=50):
    # Heuristic: bullish OB = last bearish candle preceding 3+ bar bullish move breakout
    obs = []
    for i in range(5, len(df)-1):
        # check for local bearish candle with body and next 3 closes above prior close
        prev = df.iloc[i-4:i+1]
        # simple condition: a large down candle then 2+ up closes
        c0 = df.iloc[i]
        next1 = df.iloc[i+1]
        body = abs(c0['Close'] - c0['Open'])
        range_ = c0['High'] - c0['Low']
        if body > 0 and (next1['Close'] > c0['High']):
            obs.append({"type":"bullish" if c0['Close'] < c0['Open'] else "bearish",
                        "index": df.index[i], "high": c0['High'], "low": c0['Low']})
    # dedupe & return last few
    return obs[-6:]

def detect_fvg(df):
    # Fair value gap (simple): Look for three-candle gap where middle candle creates imbalance
    fvg_zones = []
    for i in range(1, len(df)-1):
        prev = df.iloc[i-1]
        cur = df.iloc[i]
        nxt = df.iloc[i+1]
        # bullish FVG: cur.low > prev.high (gap up)
        if cur['Low'] > prev['High']:
            fvg_zones.append({"type":"bullish","start":prev.name,"end":cur.name,"low":prev['High'],"high":cur['Low']})
        # bearish FVG
        if cur['High'] < prev['Low']:
            fvg_zones.append({"type":"bearish","start":prev.name,"end":cur.name,"low":cur['High'],"high":prev['Low']})
    return fvg_zones[-8:]

def detect_bos_choch(df):
    # Simple break of structure detection by higher high / lower low sequence
    # We compute last swing highs/lows and check for recent break
    highs = df['High']
    lows = df['Low']
    last_high = highs.rolling(20).max().iloc[-2]  # previous 20-window high
    last_low = lows.rolling(20).min().iloc[-2]
    current_high = highs.iloc[-1]
    current_low = lows.iloc[-1]
    bos = None
    choch = None
    if current_high > last_high:
        bos = "bullish"
    if current_low < last_low:
        bos = "bearish" if bos is None else bos
    # CHoCH: small change detection comparing recent structure
    # if prior structure bullish and now a lower low appears => CHoCH (indicative)
    return {"bos": bos, "last_high": float(last_high), "last_low": float(last_low)}

# --- Payapa (EMA + RSI quick heuristic) ---
def payapa_signal(df):
    last = df.iloc[-1]
    # momentum extremes: rsi very low + price near ema20 -> buy
    buy = (last['rsi14'] < 35) and (last['Close'] > last['ema20'])
    sell = (last['rsi14'] > 65) and (last['Close'] < last['ema20'])
    return {"payapa_buy": bool(buy), "payapa_sell": bool(sell)}

# --- Candle Range Theory (CRT) simple flag ---
def candle_range_flags(df):
    # detect inside bars, outside bars, expansion candles
    last = df.iloc[-1]
    prev = df.iloc[-2]
    flags = {}
    flags['inside_bar'] = (last['High'] < prev['High']) and (last['Low'] > prev['Low'])
    flags['outside_bar'] = (last['High'] > prev['High']) and (last['Low'] < prev['Low'])
    flags['big_range'] = (last['High'] - last['Low']) > 1.5 * df['High'].diff().rolling(10).std().iloc[-1]
    return flags

# --- Combine all signals into final recommendation ---
def aggregate_signal(df):
    analysis = {}
    analysis['indicators'] = {}
    last = df.iloc[-1]
    analysis['indicators']['ema20'] = float(last['ema20'])
    analysis['indicators']['ema50'] = float(last['ema50'])
    analysis['indicators']['rsi14'] = float(last['rsi14'])
    analysis['indicators']['atr14'] = float(last['atr14'])
    # SMC heuristics
    analysis['order_blocks'] = detect_order_blocks(df)
    analysis['fvg'] = detect_fvg(df)
    analysis['structure'] = detect_bos_choch(df)
    analysis['payapa'] = payapa_signal(df)
    analysis['candle_flags'] = candle_range_flags(df)

    # Score-based aggregator
    score = 0.0
    reasons = []
    # EMA trend filter
    if last['ema20'] > last['ema50'] > last['ema200']:
        score += 0.8; reasons.append("strong_uptrend_EMA")
    if last['ema20'] < last['ema50'] < last['ema200']:
        score -= 0.8; reasons.append("strong_downtrend_EMA")
    # RSI
    if last['rsi14'] < 30:
        score += 0.5; reasons.append("rsi_oversold")
    if last['rsi14'] > 70:
        score -= 0.5; reasons.append("rsi_overbought")
    # Payapa
    if analysis['payapa']['payapa_buy']:
        score += 0.6; reasons.append("payapa_buy")
    if analysis['payapa']['payapa_sell']:
        score -= 0.6; reasons.append("payapa_sell")
    # BOS
    if analysis['structure']['bos'] == 'bullish':
        score += 0.4; reasons.append("bos_bull")
    if analysis['structure']['bos'] == 'bearish':
        score -= 0.4; reasons.append("bos_bear")
    # Candle Range
    if analysis['candle_flags']['outside_bar']:
        # outside bars often indicate manipulation -> cautious add
        score += 0.2; reasons.append("outside_bar")
    if analysis['c
