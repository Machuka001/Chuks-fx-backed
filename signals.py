# signals.py
def make_trade_plan(close: float, atr: float, prob_up: float):
    # Simple logic:
    # - If prob_up >= 0.55 -> BUY
    # - If prob_up <= 0.45 -> SELL
    # - Else -> NO TRADE
    direction = "FLAT"
    if prob_up >= 0.55:
        direction = "BUY"
        sl = close - 1.2 * atr
        tp = close + 2.0 * atr
    elif prob_up <= 0.45:
        direction = "SELL"
        sl = close + 1.2 * atr
        tp = close - 2.0 * atr
    else:
        sl = None
        tp = None

    return {
        "direction": direction,
        "entry": round(close, 2),
        "stop_loss": round(sl, 2) if sl else None,
        "take_profit": round(tp, 2) if tp else None,
        "notes": "ATR-based SL/TP; thresholds BUY>=0.55, SELL<=0.45"
    }
