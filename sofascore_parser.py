import os
import time
import random
import threading
import httpx
from flask import Flask, Response

# --- НАСТРОЙКИ TELEGRAM ---
BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

# --- ТВОЙ ПРОКСИ (на будущее) ---
PROXY_URL = "socks5://TvSYGxHL:H19ycY2V@158.46.145.135:64311"

# Флаг использования прокси: ставим False, чтобы пустить запросы напрямую!
USE_PROXY = False

# Список популярных мобильных User-Agent
MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
]

SENT_SIGNALS = set()
TARGET_LEAGUES = ["setka cup", "liga pro", "tt cup", "win cup", "challenger series"]

# Настраиваем клиент HTTPX в зависимости от флага
if USE_PROXY:
    limits = httpx.Limits(max_keepalive_connections=0, max_connections=5)
    client = httpx.Client(
        proxy=PROXY_URL,
        verify=False,
        limits=limits,
        timeout=20.0
    )
else:
    # Прямое подключение без прокси во избежание SSL Handshake ошибок
    client = httpx.Client(
        verify=False,
        timeout=15.0
    )


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": YOUR_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        with httpx.Client(verify=False) as tg_client:
            tg_client.post(url, json=payload, timeout=10.0)
        print("[Telegram] Сообщение отправлено!", flush=True)
    except Exception as e:
        print(f"[Telegram] Ошибка отправки: {e}", flush=True)


def get_aiscore_live():
    url = "https://isb.aiscore.com/api/v1/sport/table-tennis/events/live"
    headers = {
        "User-Agent": random.choice(MOBILE_USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://m.aiscore.com",
        "Referer": "https://m.aiscore.com/"
    }
    try:
        connection_type = "ЧЕРЕЗ ПРОКСИ" if USE_PROXY else "НАПРЯМУЮ"
        print(f"[AiScore Сеть] Делаем запрос к Live API ({connection_type})...", flush=True)
        response = client.get(url, headers=headers)
        print(f"[AiScore Сеть] Статус ответа: {response.status_code}", flush=True)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[AiScore Сеть] Ошибка подключения: {e}", flush=True)
        return None


def monitor_aiscore():
    # Небольшая задержка перед стартом мониторинга, чтобы Flask успел полностью ожить
    time.sleep(5)
    print("=== [ПОТОК] СТАРТ МОНИТОРИНГА AISCORE ===", flush=True)
    send_telegram_message("📱 <b>Бот мониторинга AiScore запущен (прямой режим)!</b>\nПроверяем доступность API.")
    
    while True:
        try:
            print("[AiScore Мониторинг] Сканируем лайв...", flush=True)
            data = get_aiscore_live()
            
            events = []
            if data:
                if isinstance(data, dict):
                    events = data.get("events", []) or data.get("data", {}).get("events", []) or []
                elif isinstance(data, list):
                    events = data
            
            if events:
                print(f"[AiScore Мониторинг] Найдено матчей в лайве: {len(events)}", flush=True)
                current_live_ids = set()
                
                for event in events:
                    event_id = event.get("id")
                    if not event_id:
                        continue
                    current_live_ids.add(event_id)
                    
                    if event_id in SENT_SIGNALS:
                        continue
                        
                    tournament = event.get("tournament", {}) or event.get("comp", {}) or {}
                    league_name = tournament.get("name", "Unknown League")
                    
                    # Фильтр по лигам
                    is_target = any(target in league_name.lower() for target in TARGET_LEAGUES)
                    if not is_target:
                        continue
                        
                    home_team = event.get("homeTeam", {}) or event.get("home", {}) or {}
                    away_team = event.get("awayTeam", {}) or event.get("away", {}) or {}
                    
                    home_name = home_team.get("name", "Player 1")
                    away_name = away_team.get("name", "Player 2")
                    
                    home_score = event.get("homeScore", {}).get("display", 0) if event.get("homeScore") else 0
                    away_score = event.get("awayScore", {}).get("display", 0) if event.get("awayScore") else 0
                    
                    msg_text = (
                        f"📱 <b>AiScore: LIVE МАТЧ!</b>\n\n"
                        f"🏆 Турнир: {league_name}\n"
                        f"🏓 Игра: <b>{home_name}</b> vs <b>{away_name}</b>\n"
                        f"📊 Текущий счет: {home_score} : {away_score}\n"
                        f"🆔 ID матча: <code>{event_id}</code>"
                    )
                    
                    print(f"[AiScore] Найдена игра {home_name} - {away_name}. Отправляю...", flush=True)
                    send_telegram_message(msg_text)
                    SENT_SIGNALS.add(event_id)
                    time.sleep(1)
                    
                # Чистим завершенные матчи
                expired_matches = SENT_SIGNALS - current_live_ids
                for expired_id in list(expired_matches):
                    SENT_SIGNALS.remove(expired_id)
            else:
                print("[AiScore Мониторинг] Лайв-матчи не найдены или пустой ответ.", flush=True)
                
        except Exception as e:
            print(f"[AiScore Мониторинг] Ошибка в цикле: {e}", flush=True)
            
        print("[AiScore Мониторинг] Круг завершен. Ждем 30 секунд...", flush=True)
        time.sleep(30)


# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

# Отключаем SERVER_NAME, чтобы Flask не падал при пингах от Render
app.config['SERVER_NAME'] = None

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return Response("HTTPX Бот работает напрямую!", status=200)

def start_monitoring():
    for thread in threading.enumerate():
        if thread.name == "AiScoreMonitor":
            return
    print("[Система] Инициализация фонового потока...", flush=True)
    monitor_thread = threading.Thread(target=monitor_aiscore, name="AiScoreMonitor", daemon=True)
    monitor_thread.start()

@app.before_request
def initialize():
    start_monitoring()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
