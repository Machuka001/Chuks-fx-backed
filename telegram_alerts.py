# telegram_alerts.py
import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram_alert(signal: dict):
    if not TOKEN or not CHAT_ID:
        return {"sent": False, "reason": "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"}
    text = (
        f"📈 Chuks FX Signal\n"
        f"Symbol: {signal.get('symbol')}\n"
        f"TF: {signal.get('timeframe')}\n"
        f"Direction: {signal.get('direction')}\n"
        f"Entry: {signal.get('entry')}\n"
        f"SL: {signal.get('stop_loss')}\n"
        f"TP: {signal.get('take_profit')}\n"
        f"Confidence: {signal.get('model_confidence')}"
    )
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text})
    ok = r.status_code == 200
    return {"sent": ok, "status_code": r.status_code}
