import os
import time
import random
import threading
import httpx
from flask import Flask

# 1. Объект app создается сразу на верхнем уровне
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
    print("--- [СИСТЕМА] Поток мониторинга запущен ---", flush=True)
    while True:
        proxy_url = random.choice(PROXIES)
        try:
            # Запрос через httpx с прокси
            resp = httpx.get(
                "https://api.sofascore.com/api/v1/sport/table-tennis/events/live",
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0,
                verify=False
            )
            print(f"--- [СЕТЬ] Прокси {proxy_url.split('@')[1]} | Статус: {resp.status_code} ---", flush=True)
        except Exception as e:
            print(f"--- [ОШИБКА] {e} ---", flush=True)
        time.sleep(60)

# 2. Запуск потока мониторинга
threading.Thread(target=monitor, daemon=True).start()

@app.route('/')
def home():
    return "Bot is running"

# 3. Блок для локального запуска
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
