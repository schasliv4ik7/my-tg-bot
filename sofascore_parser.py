import os
import time
import random
import threading
import requests
from flask import Flask

# Отключаем предупреждения SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- НАСТРОЙКИ TELEGRAM ---
BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

# --- ТВОЙ ПРОКСИ ---
PROXY_URL = "socks5://TvSYGxHL:H19ycY2V@158.46.145.135:64311"

# Список популярных мобильных агентов
MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
]

# Инициализируем сессию через прокси
session = requests.Session()
if PROXY_URL:
    session.proxies = {"http": PROXY_URL, "https": PROXY_URL}
    session.trust_env = False

SENT_SIGNALS = set()

# Список отслеживаемых лиг настольного тенниса (можно расширять)
TARGET_LEAGUES = ["setka cup", "liga pro", "tt cup", "win cup", "challenger series"]


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": YOUR_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10, verify=False)
        print("[Telegram] Сообщение отправлено!", flush=True)
    except Exception as e:
        print(f"[Telegram] Ошибка отправки: {e}", flush=True)


def get_aiscore_live():
    # Мобильный API-эндпоинт лайв матчей AiScore для настольного тенниса (ID спорта 5)
    url = "https://isb.aiscore.com/api/v1/sport/table-tennis/events/live"
    headers = {
        "User-Agent": random.choice(MOBILE_USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://m.aiscore.com",
        "Referer": "https://m.aiscore.com/"
    }
    try:
        print("[AiScore Сеть] Запрос к API лайва...", flush=True)
        response = session.get(url, headers=headers, timeout=15, verify=False)
        print(f"[AiScore Сеть] Статус ответа: {response.status_code}", flush=True)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[AiScore Сеть] Ошибка запроса: {e}", flush=True)
        return None


def monitor_aiscore():
    print("=== [ПОТОК] СТАРТ ТЕСТИРОВАНИЯ AISCORE LIVE ===", flush=True)
    send_telegram_message("📱 <b>Тест AiScore запущен!</b>\nИщу лайв-матчи по настольному теннису.")
    
    while True:
        try:
            print("[AiScore Мониторинг] Сканируем лайв...", flush=True)
            data = get_aiscore_live()
            
            # В зависимости от структуры ответа API AiScore
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
                    current_live_ids.add(event_id)
                    
                    if event_id in SENT_SIGNALS:
                        continue
                        
                    tournament = event.get("tournament", {}) or event.get("comp", {})
                    league_name = tournament.get("name", "Unknown League")
                    
                    # Проверяем, подходит ли лига под наши фильтры
                    is_target = any(target in league_name.lower() for target in TARGET_LEAGUES)
                    if not is_target:
                        continue
                        
                    home_team = event.get("homeTeam", {}) or event.get("home", {})
                    away_team = event.get("awayTeam", {}) or event.get("away", {})
                    
                    home_name = home_team.get("name", "Player 1")
                    away_name = away_team.get("name", "Player 2")
                    
                    home_score = event.get("homeScore", {}).get("display", 0)
                    away_score = event.get("awayScore", {}).get("display", 0)
                    
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
                    
                # Очистка завершенных матчей
                expired_matches = SENT_SIGNALS - current_live_ids
                for expired_id in expired_matches:
                    SENT_SIGNALS.remove(expired_id)
            else:
                print("[AiScore Мониторинг] Лайв-матчи не найдены или пустой ответ от API.", flush=True)
                
        except Exception as e:
            print(f"[AiScore Мониторинг] Ошибка в цикле: {e}", flush=True)
            
        print("[AiScore Мониторинг] Круг завершен. Ждем 30 секунд...", flush=True)
        time.sleep(30)


# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "AiScore Бот активен!"

# Принудительный старт фонового потока для Gunicorn
print("[Система] Инициализация фонового потока AiScore для Gunicorn...", flush=True)
monitor_thread = threading.Thread(target=monitor_aiscore, daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
