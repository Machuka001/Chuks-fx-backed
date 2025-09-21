# mt5_bridge.py
# Run this on a Windows machine where MetaTrader5 terminal is installed and logged in.
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import MetaTrader5 as mt5

app = FastAPI(title="MT5 Bridge")
ACTIVE_LOGIN = None

def ensure_init():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

class ConnectReq(BaseModel):
    login: str
    password: str
    server: str

@app.get("/status")
def status():
    try:
        ensure_init()
        info = mt5.terminal_info()
        vers = mt5.version()
        return {"initialized": True, "login": ACTIVE_LOGIN, "terminal": str(info), "version": vers}
    except Exception as e:
        return {"initialized": False, "error": str(e)}

@app.post("/accounts/connect")
def connect(req: ConnectReq):
    try:
        ensure_init()
        ok = mt5.login(login=int(req.login), password=req.password, server=req.server)
        if not ok:
            raise HTTPException(status_code=401, detail=f"MT5 login failed: {mt5.last_error()}")
        global ACTIVE_LOGIN; ACTIVE_LOGIN = req.login
        return {"connected": True, "login": req.login, "server": req.server}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/price")
def price(symbol: str = "XAUUSD"):
    ensure_init()
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"No tick for {symbol}")
    return {"symbol": symbol, "bid": tick.bid, "ask": tick.ask, "time": tick.time}

@app.get("/candles")
def candles(symbol: str = "XAUUSD", timeframe: str = "H1", count: int = 300):
    ensure_init()
    tf_map = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
              "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
    tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None:
        raise HTTPException(status_code=404, detail=f"Could not fetch candles for {symbol} {timeframe}")
    out = []
    for r in rates:
        out.append({"time": int(r["time"]), "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"]), "tick_volume": int(r["tick_volume"])})
    return {"symbol": symbol, "timeframe": timeframe, "count": len(out), "candles": out}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
