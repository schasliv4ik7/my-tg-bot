import os
import time
import random
import threading
import httpx
from flask import Flask, Response

app = Flask(__name__)

BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

# Твой полный список прокси
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

def send_tg(text):
    try:
        httpx.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                   json={"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=5)
    except: pass

def get_live_data():
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
    
    # Пытаемся пройти через каждый прокси из списка по очереди, если нужно
    random.shuffle(PROXIES) 
    for proxy in PROXIES:
        try:
            proxies = {"http://": proxy, "https://": proxy}
            print(f"[Сеть] Пробую прокси: {proxy.split('@')[1]}", flush=True)
            resp = httpx.get(url, headers=headers, proxies=proxies, timeout=10, verify=False)
            
            if resp.status_code == 200:
                return resp.json()
            print(f"[Сеть] Код {resp.status_code} на {proxy.split('@')[1]}", flush=True)
        except Exception as e:
            print(f"[Сеть] Ошибка {proxy.split('@')[1]}: {e}", flush=True)
    return None

def monitor():
    time.sleep(5)
    print("=== [СИСТЕМА] МОНИТОРИНГ ЗАПУЩЕН ===", flush=True)
    while True:
        data = get_live_data()
        if data:
            print("[Мониторинг] Данные получены, проверяю матчи...", flush=True)
            # Тут твоя логика уведомлений
        else:
            print("[Мониторинг] Все прокси вернули ошибку или пусто. Жду 60 сек.", flush=True)
        time.sleep(60)

@app.route('/')
def home():
    return "Bot is alive"

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
