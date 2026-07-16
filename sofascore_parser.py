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

MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.36"
]

# Инициализируем сессию с прокси
session = requests.Session()
if PROXY_URL:
    session.proxies = {"http": PROXY_URL, "https": PROXY_URL}
    session.trust_env = False

SENT_SIGNALS = set()


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": YOUR_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10, verify=False)
        print("[Telegram] Тестовое сообщение успешно отправлено!", flush=True)
    except Exception as e:
        print(f"[Telegram] Ошибка отправки сообщения: {e}", flush=True)


def make_request(url):
    headers = {
        "User-Agent": random.choice(MOBILE_USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "Cache-Control": "no-cache"
    }
    try:
        print(f"[Сеть] Запрос к {url} через прокси...", flush=True)
        response = session.get(url, headers=headers, timeout=15, verify=False)
        print(f"[Сеть] Ответ сервера: {response.status_code}", flush=True)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[Сеть] Ошибка запроса через прокси: {e}", flush=True)
        return None


def get_live_table_tennis_matches():
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    data = make_request(url)
    return data.get("events", []) if data else []


def monitor_table_tennis():
    print("=== [ПОТОК] ТЕСТОВЫЙ ЗАПУСК ЧЕРЕЗ ПРОКСИ БЕЗ ФИЛЬТРОВ ===", flush=True)
    send_telegram_message("🧪 <b>Тестовый режим через ПРОКСИ запущен!</b>\nИщу вообще любые лайв-матчи без фильтрации.")
    
    while True:
        try:
            print("[Мониторинг] Начинаем круг сканирования...", flush=True)
            matches = get_live_table_tennis_matches()
            
            if matches:
                print(f"[Мониторинг] УСПЕХ! Найдено {len(matches)} матчей в лайве SofaScore.", flush=True)
                current_live_ids = set()
                
                for match in matches:
                    event_id = match.get("id")
                    current_live_ids.add(event_id)
                    
                    if event_id in SENT_SIGNALS:
                        continue
                    
                    tournament_name = match.get("tournament", {}).get("name", "Unknown")
                    home_player = match.get("homeTeam", {}).get("name", "Player 1")
                    away_player = match.get("awayTeam", {}).get("name", "Player 2")
                    home_score = match.get("homeScore", {}).get("display", 0)
                    away_score = match.get("awayScore", {}).get("display", 0)
                    
                    msg_text = (
                        f"🧪 <b>ТЕСТОВЫЙ МАТЧ НАЙДЕН!</b>\n\n"
                        f"🏆 Лига: {tournament_name}\n"
                        f"🏓 Игра: <b>{home_player}</b> vs <b>{away_player}</b>\n"
                        f"📊 Текущий счет: {home_score} : {away_score}\n"
                        f"🆔 ID: <code>{event_id}</code>"
                    )
                    
                    print(f"[Мониторинг] Отправляю тестовый матч ID {event_id} в Телеграм...", flush=True)
                    send_telegram_message(msg_text)
                    SENT_SIGNALS.add(event_id)
                    time.sleep(1)
                
                # Чистим старые матчи
                expired_matches = SENT_SIGNALS - current_live_ids
                for expired_id in expired_matches:
                    SENT_SIGNALS.remove(expired_id)
            else:
                print("[Мониторинг] На SofaScore сейчас 0 активных лайв-игр.", flush=True)
                
        except Exception as e:
            print(f"[Мониторинг] Ошибка в цикле: {e}", flush=True)
            
        print("[Мониторинг] Круг завершен. Ждем 30 секунд...", flush=True)
        time.sleep(30)


# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Тестовый бот через прокси активен!"


# --- ЗАПУСК ПОТОКА ПРИ ИМПОРТЕ GUNICORN ---
# Выносим запуск из блока __main__, чтобы поток стартовал на Render автоматически!
print("[Система] Инициализация фонового потока для Gunicorn...", flush=True)
monitor_thread = threading.Thread(target=monitor_table_tennis, daemon=True)
monitor_thread.start()


if __name__ == "__main__":
    # Локальный запуск
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
