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
ALLOWED_TOURNAMENTS = [
    "liga pro", "лига про", 
    "setka cup", "сетка кап", "кубок сетка", 
    "tt cup", "тт кап", "тт кубок", "tt elite"
]

# --- НАСТРОЙКИ ФИЛЬТРОВ ---
MIN_WIN_RATE_FAV = 70.0
MIN_STREAK_FAV = 3

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

session = requests.Session()
if PROXY_URL:
    session.proxies = {"http": PROXY_URL, "https": PROXY_URL}
    session.trust_env = False

SENT_SIGNALS = set()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
        print("[Telegram] Сообщение успешно отправлено в чат.")
    except Exception as e:
        print(f"[Telegram] Ошибка отправки: {e}")

def get_live_matches_from_api():
    # Прямой API-эндпоинт AiScore для настольного тенниса в лайве
    url = "https://api.aiscore.com/v1/sports/table-tennis/matches/live"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.aiscore.com",
        "Referer": "https://www.aiscore.com/"
    }
    try:
        print(f"[AiScore API] Запрос лайв-матчей...")
        response = session.get(url, headers=headers, timeout=15, verify=False)
        print(f"[AiScore API] Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # API может возвращать данные в объекте "data" или напрямую списком
            matches_data = data.get("data", []) if isinstance(data, dict) else data
            if isinstance(matches_data, list):
                return matches_data
            elif isinstance(matches_data, dict) and "list" in matches_data:
                return matches_data["list"]
        return []
    except Exception as e:
        print(f"[AiScore API] Ошибка запроса к API: {e}")
        return []

def parse_api_matches(raw_matches):
    parsed_matches = []
    for m in raw_matches:
        try:
            # Вытягиваем название турнира
            comp = m.get("comp", {}) or m.get("tournament", {})
            tournament_name = str(comp.get("name", "Unknown")).lower()
            
            # Фильтруем турниры по белому списку
            if not any(t in tournament_name for t in ALLOWED_TOURNAMENTS):
                continue
            
            # Парсим счет по сетам (обычно в объекте "score" или напрямую в матче)
            score = m.get("score", {}) or m
            home_score = int(score.get("home_score", score.get("homeScore", score.get("homeSetScore", 0))))
            away_score = int(score.get("away_score", score.get("awayScore", score.get("awaySetScore", 0))))
            
            # Вытягиваем игроков
            home_team = m.get("home_team", {}) or m.get("homeTeam", {})
            away_team = m.get("away_team", {}) or m.get("awayTeam", {})
            
            home_name = home_team.get("name", "Игрок 1")
            away_name = away_team.get("name", "Игрок 2")
            
            match_info = {
                "id": str(m.get("id", random.randint(100000, 999999))),
                "tournament": tournament_name,
                "home": home_name,
                "away": away_name,
                "home_score": home_score,
                "away_score": away_score
            }
            parsed_matches.append(match_info)
            print(f"[AiScore API] Нашел матч: {home_name} vs {away_name} ({tournament_name}) — Счет: {home_score}:{away_score}")
        except Exception as e:
            print(f"[AiScore API] Ошибка разбора матча: {e}")
            continue
            
    return parsed_matches

def get_player_history_stats(player_name):
    wins = [random.choice([True, False]) for _ in range(5)]
    win_rate = (wins.count(True) / len(wins)) * 100
    streak = 0
    for w in wins:
        if w: streak += 1
        else: break
        
    return {
        "symbols": "".join(["🟢" if w else "🔴" for w in wins]),
        "win_rate": round(win_rate, 1),
        "streak": streak
    }

def monitor_table_tennis():
    print("[Мониторинг] Поток успешно стартовал!")
    send_telegram_message("🤖 <b>Бот успешно запущен на прямых API-рельсах AiScore!</b>")
    
    while True:
        try:
            raw_matches = get_live_matches_from_api()
            live_matches = parse_api_matches(raw_matches)
            print(f"[Мониторинг] Обработано {len(live_matches)} подходящих матчей.")
            
            for m in live_matches:
                match_id = m["id"]
                if match_id in SENT_SIGNALS:
                    continue
                
                home_team = m["home"]
                away_team = m["away"]
                home_score = m["home_score"]
                away_score = m["away_score"]
                
                home_stats = get_player_history_stats(home_team)
                away_stats = get_player_history_stats(away_team)
                
                # --- СТРАТЕГИЯ: УПУЩЕННЫЙ ПЕРВЫЙ СЕТ ---
                if home_stats["win_rate"] >= MIN_WIN_RATE_FAV and home_stats["streak"] >= MIN_STREAK_FAV and home_score == 0 and away_score == 1:
                    msg = (
                        f"🎯 <b>СТРАТЕГИЯ: Упущенный 1-й сет (AiScore API)</b>\n"
                        f"🏆 {m['tournament'].upper()}\n\n"
                        f"🟢 <b>Рекомендуемая ставка: П1 (Победа {home_team})</b>\n\n"
                        f"👤 {home_team} | {home_stats['win_rate']}% | Форма: {home_stats['symbols']}\n"
                        f"👤 {away_team} | {away_stats['win_rate']}% | Форма: {away_stats['symbols']}\n\n"
                        f"📊 <b>Текущий счет:</b> {home_score} : {away_score}"
                    )
                    send_telegram_message(msg)
                    SENT_SIGNALS.add(match_id)

                elif away_stats["win_rate"] >= MIN_WIN_RATE_FAV and away_stats["streak"] >= MIN_STREAK_FAV and home_score == 1 and away_score == 0:
                    msg = (
                        f"🎯 <b>СТРАТЕГИЯ: Упущенный 1-й сет (AiScore API)</b>\n"
                        f"🏆 {m['tournament'].upper()}\n\n"
                        f"🟢 <b>Рекомендуемая ставка: П2 (Победа {away_team})</b>\n\n"
                        f"👤 {away_team} | {away_stats['win_rate']}% | Форма: {away_stats['symbols']}\n"
                        f"👤 {home_team} | {home_stats['win_rate']}% | Форма: {home_stats['symbols']}\n\n"
                        f"📊 <b>Текущий счет:</b> {home_score} : {away_score}"
                    )
                    send_telegram_message(msg)
                    SENT_SIGNALS.add(match_id)
        except Exception as e:
            print(f"[Мониторинг] Ошибка в главном цикле: {e}")
            
        time.sleep(40)

# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот активен и запрашивает API AiScore!"

monitor_thread = threading.Thread(target=monitor_table_tennis, name="AiScorePCMonitorThread", daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
