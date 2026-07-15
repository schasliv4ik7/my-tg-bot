import os
import time
import random
import threading
import requests
from flask import Flask

# Отключаем предупреждения об отсутствии SSL-верификации
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- НАСТРОЙКИ TELEGRAM ---
BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

# --- ТВОЙ ПРИВАТНЫЙ ПРОКСИ ---
PROXY_URL = "socks5://TvSYGxHL:H19ycY2V@158.46.145.135:64311"

# --- БЕЛЫЙ СПИСОК ТУРНИРОВ ---
ALLOWED_TOURNAMENTS = ["liga pro", "setka cup", "tt cup"]

# --- НАСТРОЙКИ ФИЛЬТРОВ ---
MIN_WIN_RATE_FAV = 70.0
MIN_STREAK_FAV = 3
MIN_WIN_RATE_EQUAL = 55.0
MIN_STREAK_EQUAL = 2

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
]

# --- НАСТРОЙКА СЕССИИ С ИЗОЛЯЦИЕЙ ТРАФИКА ---
session = requests.Session()
if PROXY_URL:
    session.proxies = {"http": PROXY_URL, "https": PROXY_URL}
    session.trust_env = False  # Исключает утечку трафика мимо прокси

SENT_SIGNALS = set()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[Telegram] Ошибка: {e}")

def make_request(url, silent_404=False):
    headers = {"User-Agent": random.choice(USER_AGENTS), "Connection": "keep-alive"}
    try:
        response = session.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200: return response.json()
        if response.status_code == 403: print("[Ошибка]: 403 Forbidden (Блокировка IP)")
        return None
    except Exception as e:
        print(f"[Ошибка запроса]: {e}")
        return None

def get_player_stats(match_id, side):
    data = make_request(f"https://api.sofascore.com/api/v1/event/{match_id}/team-events/{side}", silent_404=True)
    if not data or "events" not in data: return {"symbols": "Нет данных", "win_rate": 0.0, "streak": 0}
    
    events = data.get("events", [])[:5]
    wins = []
    for e in events:
        h_score = e.get("homeScore", {}).get("display")
        a_score = e.get("awayScore", {}).get("display")
        if h_score is None or a_score is None: continue
        target_id = e.get("homeTeam", {}).get("id") if side == "home" else e.get("awayTeam", {}).get("id")
        wins.append((h_score > a_score) if target_id == e.get("homeTeam", {}).get("id") else (a_score > h_score))
        
    win_rate = (wins.count(True) / len(wins)) * 100 if wins else 0
    streak = 0
    for w in wins:
        if w: streak += 1
        else: break
    return {"symbols": "".join(["🟢" if w else "🔴" for w in wins]), "win_rate": round(win_rate, 1), "streak": streak}

def monitor_table_tennis():
    send_telegram_message(
        f"🤖 <b>Фильтр запущен!</b>\n\n"
        f"1️⃣ <b>Камбэк фаворита:</b> винрейт {MIN_WIN_RATE_FAV}%, стрик {MIN_STREAK_FAV}\n"
        f"2️⃣ <b>Равная игра ТОП:</b> винрейт {MIN_WIN_RATE_EQUAL}%, стрик {MIN_STREAK_EQUAL}"
    )
    while True:
        matches = make_request("https://api.sofascore.com/api/v1/sport/table-tennis/events/live")
        if matches and "events" in matches:
            for m in matches["events"]:
                if m.get("id") in SENT_SIGNALS: continue
                # (Логика анализа и отправки сигналов)
                # ...
        time.sleep(45)

app = Flask(__name__)
@app.before_request
def start_monitoring():
    if not any(t.name == "SofascoreMonitorThread" for t in threading.enumerate()):
        threading.Thread(target=monitor_table_tennis, name="SofascoreMonitorThread", daemon=True).start()

@app.route('/')
def home(): return "Бот активен!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
