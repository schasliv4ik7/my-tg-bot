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

# Используем прокси
PROXY_URL = "http://aeeufstt:mmzjzap1e8nc@84.247.60.125:6095"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        httpx.post(url, json=payload, timeout=10.0)
    except Exception as e:
        print(f"[Telegram] Ошибка: {e}", flush=True)

def get_sofascore_live():
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    # Добавляем больше заголовков для имитации браузера
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Referer": "https://www.sofascore.com/",
        "Accept": "application/json",
        "Cache-Control": "no-cache"
    }
    try:
        # Явное использование прокси через прокси-словарь
        proxies = {"http://": PROXY_URL, "https://": PROXY_URL}
        print("[Сеть] Запрос через прокси...", flush=True)
        response = httpx.get(url, headers=headers, proxies=proxies, timeout=15.0, verify=False)
        print(f"[Сеть] Статус: {response.status_code}", flush=True)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"[Сеть] Ошибка: {e}", flush=True)
        return None

def monitor_sofascore():
    time.sleep(5)
    while True:
        data = get_sofascore_live()
        # ... (логика обработки та же)
        time.sleep(60) # Увеличим интервал, чтобы не спамить

@app.route('/')
def home():
    return "Bot is running"

if __name__ == "__main__":
    threading.Thread(target=monitor_sofascore, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
