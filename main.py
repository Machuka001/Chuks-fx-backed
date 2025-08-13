# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

from ai_model import train_model, load_model, predict_latest_signal
from data import fetch_history
from telegram_alerts import send_telegram_alert

app = FastAPI(title="Chuks FX Strategy Backend (AI)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

USERNAME = "chuks fx"
PASSWORD = "2345678901"
STATE = {"bot_running": False}

class Login(BaseModel):
    username: str
    password: str

class TrainReq(BaseModel):
    period_days: int = 180       # how far back to train
    symbol: str = "XAUUSD=X"     # Yahoo Finance Gold/USD symbol
    interval: str = "1h"         # 1-hour timeframe

class AnalyzeReq(BaseModel):
    symbol: str = "XAUUSD=X"
    interval: str = "1h"
    notify_telegram: bool = False

@app.get("/")
def health():
    return {"message": "Chuks FX Backend Live"}

@app.post("/login")
def login(body: Login):
    if body.username == USERNAME and body.password == PASSWORD:
        return {"ok": True}
    raise HTTPException(401, "Invalid credentials")

@app.post("/start-bot")
def start_bot():
    STATE["bot_running"] = True
    return {"message": "Bot flag set to running (use /analyze-now for on-demand signals)."}

@app.post("/stop-bot")
def stop_bot():
    STATE["bot_running"] = False
    return {"message": "Bot stopped"}

@app.post("/train")
def train(req: TrainReq):
    try:
        df = fetch_history(req.symbol, req.interval, req.period_days)
        metrics = train_model(df)      # saves to /tmp/chuks_fx_model.pkl
        return {"status": "trained", "metrics": metrics}
    except Exception as e:
        raise HTTPException(500, f"Training failed: {e}")

@app.post("/analyze-now")
def analyze(req: AnalyzeReq):
    try:
        result = predict_latest_signal(req.symbol, req.interval)
        if req.notify_telegram:
            send_telegram_alert(result)
        return {"status": "ok", "signal": result}
    except FileNotFoundError:
        raise HTTPException(400, "Model not trained yet. Call /train first.")
    except Exception as e:
        raise HTTPException(500, f"Analyze failed: {e}")
from tv_ai_engine import analyze_xau_tradingview_style

@app.post("/analyze-tradingview")
def analyze_tradingview(period_days: int = 365):
    try:
        res = analyze_xau_tradingview_style(period_days=period_days, interval="1h")
        # optionally send Telegram here
        return {"status":"ok","data":res}
    except Exception as e:
        raise HTTPException(500, str(e))
