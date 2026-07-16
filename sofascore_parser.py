import os
import time
import random
import threading
import httpx
from flask import Flask, Response

app = Flask(__name__)

PROXIES = [
    "http://aeeufstt:mmzjzap1e8nc@31.59.20.176:6754",
    "http://aeeufstt:mmzjzap1e8nc@31.56.127.193:7684",
    "http://aeeufstt:mmzjzap1e8nc@45.38.107.97:6014",
    "http://aeeufstt:mmzjzap1e8nc@198.105.121.200:6462",
    "http://aeeufstt:mmzjzap1e8nc@64.137.96.74:6641",
    "http://aeeufstt:mmzjzap1e8nc@198.23.243.226:6361",
    "http://aeeufstt:mmzjzap1e8nc@38.154.185.97:6370",
    "http://aeeufstt:mmzjzap1e8nc@84.247.60.125:6095",
    "http://aeeufstt:mmzjzap1e8nc@142.111.67.146:5611",
    "http://aeeufstt:mmzjzap1e8nc@191.96.254.138:6185"
]

def monitor():
    print("--- [СИСТЕМА] Поток мониторинга начал выполнение ---", flush=True)
    while True:
        try:
            proxy = random.choice(PROXIES)
            print(f"--- [СЕТЬ] Попытка через: {proxy.split('@')[1]} ---", flush=True)
            
            with httpx.Client(proxies={"http://": proxy, "https://": proxy}, timeout=15.0, verify=False) as client:
                resp = client.get("https://api.sofascore.com/api/v1/sport/table-tennis/events/live", 
                                 headers={"User-Agent": "Mozilla/5.0"}, timeout=15.0)
                
            print(f"--- [СЕТЬ] Статус ответа: {resp.status_code} ---", flush=True)
            if resp.status_code == 200:
                print("--- [УСПЕХ] Данные получены! ---", flush=True)
            else:
                print(f"--- [ОШИБКА] Состояние: {resp.status_code} ---", flush=True)
        except Exception as e:
            print(f"--- [КРИТИЧЕСКАЯ ОШИБКА] {str(e)} ---", flush=True)
            
        time.sleep(30)

@app.route('/')
def home():
    return "Bot is running"

# Принудительный запуск мониторинга при старте Flask
@app.before_first_request
def start_monitor_thread():
    threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
