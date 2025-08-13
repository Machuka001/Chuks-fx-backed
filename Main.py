# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

app = FastAPI(title="Chuks FX Strategy Backend")

# Allow frontend access (wide-open for now; tighten later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# --- Simple in-memory state (replace with DB later) ---
STATE = {
    "bot_running": False,
    "risk": {"risk_per_trade": 1.0, "max_drawdown": 10.0, "max_trades_per_day": 5},
    "strategies": {"order_blocks": True, "fvg": True, "choch": True, "candle_range": True},
    "performance": {"total_trades": 0, "win_rate": 0.0, "profit_percent": 0.0, "missed_trades": 0}
}

USERNAME = "chuks fx"
PASSWORD = "2345678901"

class Login(BaseModel):
    username: str
    password: str

class Risk(BaseModel):
    risk_per_trade: float
    max_drawdown: float
    max_trades_per_day: int

class Strategies(BaseModel):
    order_blocks: bool
    fvg: bool
    choch: bool
    candle_range: bool

@app.get("/")
def health():
    return {"message": "Chuks FX Backend Live"}

@app.post("/login")
def login(body: Login):
    if body.username == USERNAME and body.password == PASSWORD:
        return {"ok": True}
    raise HTTPException(401, "Invalid credentials")

@app.get("/status")
def status():
    return {"bot_running": STATE["bot_running"]}

@app.post("/start")
def start():
    STATE["bot_running"] = True
    return {"message": "Bot started"}

@app.post("/stop")
def stop():
    STATE["bot_running"] = False
    return {"message": "Bot stopped"}

@app.get("/risk")
def get_risk():
    return STATE["risk"]

@app.post("/risk")
def set_risk(risk: Risk):
    STATE["risk"] = risk.dict()
    return {"message": "Risk updated", "risk": STATE["risk"]}

@app.get("/strategies")
def get_strategies():
    return STATE["strategies"]

@app.post("/strategies")
def set_strategies(s: Strategies):
    STATE["strategies"] = s.dict()
    return {"message": "Strategies updated", "strategies": STATE["strategies"]}

@app.get("/performance")
def performance():
    return STATE["performance"]

# Render sets $PORT; uvicorn will use it via start command
