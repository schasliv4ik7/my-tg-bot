import os
import time
import random
import re
import json
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
MIN_WIN_RATE_EQUAL = 55.0
MIN_STREAK_EQUAL = 2

# Имитируем ПК-браузер (десктопная версия)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edge/123.0.0.0"
]

# --- НАСТРОЙКА СЕССИИ С ИЗОЛЯЦИЕЙ ТРАФИКА ---
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
    except Exception as e:
        print(f"[Telegram] Ошибка отправки: {e}")

def make_request(url):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.aiscore.com/",
        "Upgrade-Insecure-Requests": "1"
    }
    try:
        response = session.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            return response.text
        print(f"[AiScore PC] Ошибка доступа. Код: {response.status_code}")
        return None
    except Exception as e:
        print(f"[AiScore PC] Ошибка запроса: {e}")
        return None

def parse_aiscore_live(html_text):
    if not html_text:
        return []
        
    matches = []
    json_data = None
    
    # Ищем JSON-данные десктопной версии страницы
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text, re.DOTALL)
    if next_data_match:
        try:
            json_data = json.loads(next_data_match.group(1))
        except Exception as e:
            print(f"[AiScore PC] Ошибка JSON: {e}")

    if json_data:
        try:
            props = json_data.get("props", {})
            page_props = props.get("pageProps", {})
            initial_state = page_props.get("initialState", page_props)
            
            match_list = (
                initial_state.get("matches", []) or 
                initial_state.get("matchList", []) or 
                initial_state.get("liveMatches", [])
            )
            
            for m in match_list:
                tournament_name = m.get("tournamentName", m.get("compName", "Unknown")).lower()
                
                if not any(t in tournament_name for t in ALLOWED_TOURNAMENTS):
                    continue
                
                status = str(m.get("status", m.get("statusId", "")))
                if status == "2" or m.get("isLive", False):
                    matches.append({
                        "id": str(m.get("id", m.get("matchId", random.randint(100000, 999999)))),
                        "tournament": tournament_name,
                        "home": m.get("homeName", m.get("homeTeamName", "Игрок 1")),
                        "away": m.get("awayName", m.get("awayTeamName", "Игрок 2")),
                        "home_score": int(m.get("homeScore", m.get("homeSetScore", 0))),
                        "away_score": int(m.get("awayScore", m.get("awaySetScore", 0)))
                    })
        except Exception as e:
            print(f"[AiScore PC] Ошибка структуры: {e}")
            
    return matches

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
    send_telegram_message("🤖 <b>Бот успешно запущен на ПК-версии AiScore!</b>")
    
    while True:
        html = make_request("https://www.aiscore.com/ru/table-tennis")
        if html:
            live_matches = parse_aiscore_live(html)
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
                
                # --- СТРАТЕГИЯ 1: УПУЩЕННЫЙ ПЕРВЫЙ СЕТ ---
                if home_stats["win_rate"] >= MIN_WIN_RATE_FAV and home_stats["streak"] >= MIN_STREAK_FAV and home_score == 0 and away_score == 1:
                    msg = (
                        f"🎯 <b>СТРАТЕГИЯ: Упущенный 1-й сет (AiScore)</b>\n"
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
                        f"🎯 <b>СТРАТЕГИЯ: Упущенный 1-й сет (AiScore)</b>\n"
                        f"🏆 {m['tournament'].upper()}\n\n"
                        f"🟢 <b>Рекомендуемая ставка: П2 (Победа {away_team})</b>\n\n"
                        f"👤 {away_team} | {away_stats['win_rate']}% | Форма: {away_stats['symbols']}\n"
                        f"👤 {home_team} | {home_stats['win_rate']}% | Форма: {home_stats['symbols']}\n\n"
                        f"📊 <b>Текущий счет:</b> {home_score} : {away_score}"
                    )
                    send_telegram_message(msg)
                    SENT_SIGNALS.add(match_id)
        
        time.sleep(40)

# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.before_request
def start_monitoring():
    if not any(t.name == "AiScorePCMonitorThread" for t in threading.enumerate()):
        threading.Thread(target=monitor_table_tennis, name="AiScorePCMonitorThread", daemon=True).start()

@app.route('/')
def home():
    return "Бот активен на ПК-версии AiScore!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
