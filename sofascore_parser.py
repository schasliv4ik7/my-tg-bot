import os
import json
import urllib.request
import urllib.parse
import time
import ssl
import threading
from urllib.error import HTTPError
from flask import Flask

# --- НАСТРОЙКИ TELEGRAM ---
BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com"
}

SSL_CONTEXT = ssl._create_unverified_context()
SENT_SIGNALS = set()


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": YOUR_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
            if response.status == 200:
                print("[Telegram] Тестовое сообщение отправлено!", flush=True)
    except Exception as e:
        print(f"[Telegram] Ошибка отправки сообщения: {e}", flush=True)


def make_request(url):
    try:
        print(f"[Сеть] Делаем запрос к {url}...", flush=True)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as response:
            print(f"[Сеть] Ответ сервера: {response.status}", flush=True)
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
            return None
    except HTTPError as e:
        print(f"[Сеть] HTTP Ошибка {e.code}: {e.reason}", flush=True)
        return None
    except Exception as e:
        print(f"[Сеть] Ошибка запроса: {e}", flush=True)
        return None


def get_live_table_tennis_matches():
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    data = make_request(url)
    if data:
        return data.get("events", [])
    return []


def monitor_table_tennis():
    print("=== [ПОТОК] Фоновый мониторинг запущен! ===", flush=True)
    send_telegram_message("🧪 <b>Тестовый режим запущен!</b>\nБот пришлет абсолютно ВСЕ лайв-матчи без фильтров.")
    
    while True:
        try:
            print("[Мониторинг] Начинаем круг сканирования...", flush=True)
            matches = get_live_table_tennis_matches()
            
            if matches:
                print(f"[Мониторинг] Найдено {len(matches)} матчей в лайве SofaScore.", flush=True)
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
                        f"📊 Текущий счет по сетам: {home_score} : {away_score}\n"
                        f"🆔 Event ID: <code>{event_id}</code>"
                    )
                    
                    print(f"[Мониторинг] Нашли новый матч ID {event_id}. Отправляем в TG...", flush=True)
                    send_telegram_message(msg_text)
                    SENT_SIGNALS.add(event_id)
                    time.sleep(1)
                
                expired_matches = SENT_SIGNALS - current_live_ids
                for expired_id in expired_matches:
                    SENT_SIGNALS.remove(expired_id)
            else:
                print("[Мониторинг] На SofaScore сейчас 0 активных лайв-игр.", flush=True)
                
        except Exception as e:
            print(f"[Мониторинг] Критическая ошибка в цикле: {e}", flush=True)
            
        print("[Мониторинг] Круг завершен. Ждем 30 секунд...", flush=True)
        time.sleep(30)


# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Тестовый бот запущен!"

# Создаем и принудительно стартуем поток перед запуском Flask
monitor_thread = threading.Thread(target=monitor_table_tennis, daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
