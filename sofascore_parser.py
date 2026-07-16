import os
import time
import random
import threading
import httpx
from flask import Flask, Response

app = Flask(__name__)

BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

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
    print("--- МОНИТОРИНГ ЗАПУЩЕН ---", flush=True)
    while True:
        url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
        
        proxy = random.choice(PROXIES)
        print(f"Попытка через: {proxy.split('@')[1]}", flush=True)
        
        try:
            resp = httpx.get(url, headers=headers, proxies={"http://": proxy, "https://": proxy}, timeout=10, verify=False)
            print(f"Результат: {resp.status_code}", flush=True)
            
            if resp.status_code == 200:
                print("УСПЕХ! Данные получены.", flush=True)
                # Здесь будет твоя логика отправки в TG
            else:
                print(f"Ошибка {resp.status_code} на прокси {proxy.split('@')[1]}", flush=True)
        except Exception as e:
            print(f"Ошибка соединения через {proxy.split('@')[1]}: {e}", flush=True)
            
        time.sleep(30)

@app.route('/')
def home():
    return "Bot is active"

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
