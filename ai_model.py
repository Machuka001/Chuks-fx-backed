# ai_model.py
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

from data import fetch_history
from signals import make_trade_plan

MODEL_PATH = "/tmp/chuks_fx_model.pkl"

def _make_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["return"] = df["Close"].pct_change()
    df["ema_20"] = EMAIndicator(df["Close"], window=20).ema_indicator()
    df["ema_50"] = EMAIndicator(df["Close"], window=50).ema_indicator()
    df["rsi_14"] = RSIIndicator(df["Close"], window=14).rsi()
    atr = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=14)
    df["atr_14"] = atr.average_true_range()

    # Targets: next bar direction (1=up, 0=down)
    df["target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

    df = df.dropna()
    features = df[["return", "ema_20", "ema_50", "rsi_14", "atr_14"]]
    target = df["target"]
    return features, target, df

def train_model(df: pd.DataFrame):
    X, y, df_feat = _make_features(df)
    if len(X) < 200:
        raise ValueError("Not enough data to train. Try increasing period_days.")

    # Simple baseline model
    model = LogisticRegression(max_iter=1000)
    # Train/test split (last 20% as test)
    split = int(len(X) * 0.8)
    X_train, y_train = X.iloc[:split], y.iloc[:split]
    X_test, y_test = X.iloc[split:], y.iloc[split:]

    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = float(accuracy_score(y_test, preds))

    joblib.dump(model, MODEL_PATH)
    return {"accuracy": round(acc, 4), "train_samples": int(len(X_train)), "test_samples": int(len(X_test))}

def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Model not found.")
    return joblib.load(MODEL_PATH)

def predict_latest_signal(symbol="XAUUSD=X", interval="1h"):
    # Load model
    model = load_model()
    # Fetch recent data (small slice to build features)
    df = fetch_history(symbol, interval, period_days=30)
    X, _, df_feat = _make_features(df)
    if len(X) == 0:
        raise ValueError("Insufficient data to compute features.")

    # Use the latest row
    x_last = X.iloc[[-1]]
    prob_up = float(model.predict_proba(x_last)[0][1])
    latest_row = df_feat.iloc[-1]

    # Build a simple trade plan based on probability and ATR
    trade = make_trade_plan(
        close=float(latest_row["Close"]),
        atr=float(latest_row["atr_14"]),
        prob_up=prob_up
    )
    trade["symbol"] = symbol
    trade["timeframe"] = interval
    trade["model_confidence"] = round(prob_up, 3)
    return trade
