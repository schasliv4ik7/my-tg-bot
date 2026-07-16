import os
import time
import random
import threading
import httpx
from flask import Flask, Response

app = Flask(__name__)
app.config['SERVER_NAME'] = None

BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

# --- ТВОЙ СПИСОК ПРОКСИ ---
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

def get_random_proxy():
    return random.choice(PROXIES)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        httpx.post(url, json=payload, timeout=10.0)
    except Exception as e:
        print(f"[Telegram] Ошибка: {e}", flush=True)

def get_sofascore_live():
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Referer": "https://www.sofascore.com/"
    }
    
    # Пытаемся сделать запрос с рандомным прокси
    proxy_url = get_random_proxy()
    proxies = {"http://": proxy_url, "https://": proxy_url}
    
    try:
        print(f"[Сеть] Запрос через прокси: {proxy_url.split('@')[1]}", flush=True)
        response = httpx.get(url, headers=headers, proxies=proxies, timeout=15.0, verify=False)
        print(f"[Сеть] Статус: {response.status_code}", flush=True)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"[Сеть] Ошибка: {e}", flush=True)
        return None

def monitor_sofascore():
    time.sleep(10)
    while True:
        data = get_sofascore_live()
        if data:
            print("[Мониторинг] Данные получены успешно!", flush=True)
            # Тут будет твоя логика парсинга
        else:
            print("[Мониторинг] Ошибка или нет лайв-матчей, пробуем через 30 сек...", flush=True)
        time.sleep(30)

@app.route('/')
def home():
    return "Bot is running with proxy rotation"

if __name__ == "__main__":
    threading.Thread(target=monitor_sofascore, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
