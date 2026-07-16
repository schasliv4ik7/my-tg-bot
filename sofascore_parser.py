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
    print("--- [СТАРТ] Мониторинг запущен принудительно ---", flush=True)
    while True:
        # Берем случайный прокси из списка
        proxy = random.choice(PROXIES)
        print(f"--- Пытаюсь использовать прокси: {proxy.split('@')[1]} ---", flush=True)
        
        try:
            client = httpx.Client(proxies={"http://": proxy, "https://": proxy}, timeout=10.0, verify=False)
            resp = client.get("https://api.sofascore.com/api/v1/sport/table-tennis/events/live", 
                             headers={"User-Agent": "Mozilla/5.0"}, timeout=10.0)
            
            print(f"--- Статус ответа: {resp.status_code} ---", flush=True)
            if resp.status_code == 200:
                print(f"--- УСПЕХ! Данные получены ---", flush=True)
            else:
                print(f"--- Ошибка: {resp.status_code}. Пробуем другой прокси через 60 сек ---", flush=True)
        except Exception as e:
            print(f"--- Критическая ошибка прокси: {e} ---", flush=True)
            
        time.sleep(60)

@app.route('/')
def home():
    return "Bot is running"

if __name__ == "__main__":
    # Запускаем мониторинг как отдельный поток
    threading.Thread(target=monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
