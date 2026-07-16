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

# --- ТВОЙ ПОЛЬСКИЙ ПРОКСИ ---
PROXY_URL = "socks5://TvSYGxHL:H19ycY2V@158.46.145.135:64311"

# Инициализируем сессию через прокси
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
        print("[Telegram] Тестовое сообщение отправлено!", flush=True)
    except Exception as e:
        print(f"[Telegram] Ошибка отправки: {e}", flush=True)


def get_sts_live_matches():
    # Официальный лайв-API STS
    url = "https://www.sts.pl/api/sports/v1/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.sts.pl/",
        "Origin": "https://www.sts.pl"
    }
    try:
        print(f"[STS Сеть] Запрос к live-API через польский прокси...", flush=True)
        response = session.get(url, headers=headers, timeout=15, verify=False)
        print(f"[STS Сеть] Статус ответа: {response.status_code}", flush=True)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[STS Сеть] Ошибка при подключении к STS: {e}", flush=True)
        return None


def monitor_sts():
    print("=== [ПОТОК] СТАРТ ТЕСТИРОВАНИЯ STS LIVE ===", flush=True)
    send_telegram_message("🇵🇱 <b>Тест STS запущен!</b>\nПроверяю доступ к линии польского букмекера.")
    
    while True:
        try:
            print("[STS Мониторинг] Сканируем лайв...", flush=True)
            data = get_sts_live_matches()
            
            if data and "sports" in data:
                found_any_table_tennis = False
                current_live_ids = set()
                
                for sport in data["sports"]:
                    # Ищем категорию настольного тенниса по-польски или по-английски
                    sport_name = sport.get("name", "").lower()
                    if "tenis stołowy" in sport_name or "table tennis" in sport_name:
                        found_any_table_tennis = True
                        
                        # Парсим регионы и лиги
                        for region in sport.get("regions", []):
                            for league in region.get("leagues", []):
                                league_name = league.get("name", "Unknown League")
                                
                                # Парсим матчи
                                for match in league.get("matches", []):
                                    match_id = match.get("id")
                                    current_live_ids.add(match_id)
                                    
                                    if match_id in SENT_SIGNALS:
                                        continue
                                    
                                    home_team = match.get("homeTeamName", "Home Player")
                                    away_team = match.get("awayTeamName", "Away Player")
                                    
                                    # Парсим текущий счет (если доступен в API)
                                    score = match.get("score", {})
                                    home_score = score.get("home", 0)
                                    away_score = score.get("away", 0)
                                    
                                    # Извлекаем основные кэфы на победу (П1 / П2)
                                    odds_p1, odds_p2 = "—", "—"
                                    for market in match.get("markets", []):
                                        if market.get("name") in ["Winner", "Mecz"]:
                                            rates = market.get("rates", [])
                                            if len(rates) >= 2:
                                                odds_p1 = rates[0].get("rateValue", "—")
                                                odds_p2 = rates[1].get("rateValue", "—")
                                    
                                    msg_text = (
                                        f"🇵🇱 <b>STS: НАЙДЕН LIVE МАТЧ!</b>\n\n"
                                        f"🏆 Турнир: {league_name}\n"
                                        f"🏓 Пара: <b>{home_team}</b> vs <b>{away_team}</b>\n"
                                        f"📊 Счет по сетам: {home_score} : {away_score}\n"
                                        f"📈 Кэфы в лайве: П1 [<code>{odds_p1}</code>] | П2 [<code>{odds_p2}</code>]\n"
                                        f"🆔 ID матча: <code>{match_id}</code>"
                                    )
                                    
                                    print(f"[STS] Найдена игра {home_team} - {away_team}. Отправляю...", flush=True)
                                    send_telegram_message(msg_text)
                                    SENT_SIGNALS.add(match_id)
                                    time.sleep(1)
                
                # Чистим завершенные матчи из памяти
                expired_matches = SENT_SIGNALS - current_live_ids
                for expired_id in expired_matches:
                    SENT_SIGNALS.remove(expired_id)
                
                if not found_any_table_tennis:
                    print("[STS Мониторинг] Настольный теннис сейчас отсутствует в лайве STS.", flush=True)
            else:
                print("[STS Мониторинг] Не удалось прочитать структуру спорта из API.", flush=True)
                
        except Exception as e:
            print(f"[STS Мониторинг] Ошибка в цикле: {e}", flush=True)
            
        print("[STS Мониторинг] Круг завершен. Ждем 30 секунд...", flush=True)
        time.sleep(30)


# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "STS Тестовый бот запущен!"

# Принудительный старт потока для Gunicorn
print("[Система] Инициализация фонового потока STS для Gunicorn...", flush=True)
monitor_thread = threading.Thread(target=monitor_sts, daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
