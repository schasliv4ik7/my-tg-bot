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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

# --- НАСТРОЙКА СЕССИИ С ИЗОЛЯЦИЕЙ ТРАФИКА ---
session = requests.Session()
if PROXY_URL:
    session.proxies = {"http": PROXY_URL, "https": PROXY_URL}
    session.trust_env = False  # Исключаем утечку трафика мимо прокси на Render

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
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.livesport.cz/stolnitennis/",
        "X-Fsign": "SW9D1eZo"
    }
    try:
        response = session.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            return response.text
        print(f"[Livesport] Ошибка доступа. Код: {response.status_code}")
        return None
    except Exception as e:
        print(f"[Livesport] Ошибка запроса: {e}")
        return None

def parse_flashscore_live(feed_text):
    if not feed_text:
        return []
        
    matches = []
    sections = feed_text.split("~")
    current_tournament = ""
    
    for section in sections:
        if section.startswith("ZA"):  # Имя турнира
            current_tournament = section.split("÷")[1].lower() if "÷" in section else ""
            continue
            
        if not any(t in current_tournament for t in ALLOWED_TOURNAMENTS):
            continue
            
        if section.startswith("AA"):  # Данные матча
            parts = section.split("¬")
            match_data = {}
            for part in parts:
                if "÷" in part:
                    key, val = part.split("÷", 1)
                    match_data[key] = val
            
            match_id = match_data.get("AA")
            status = match_data.get("AD")  # 3 означает "в игре"
            
            if status == "3" and match_id:
                home_player = match_data.get("AE", "Игрок 1")
                away_player = match_data.get("AF", "Игрок 2")
                home_score = int(match_data.get("AG", 0))
                away_score = int(match_data.get("AH", 0))
                
                matches.append({
                    "id": match_id,
                    "tournament": current_tournament,
                    "home": home_player,
                    "away": away_player,
                    "home_score": home_score,
                    "away_score": away_score
                })
    return matches

def get_player_history_stats(player_name):
    # Симуляция сбора статистики (последние 5 игр) для Livesport
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
    send_telegram_message(
        f"🤖 <b>Бот переключен на Livesport/Flashscore!</b>\n\n"
        f"1️⃣ <b>Камбэк фаворита:</b> винрейт {MIN_WIN_RATE_FAV}%, стрик {MIN_STREAK_FAV}\n"
        f"2️⃣ <b>Равная игра ТОП:</b> винрейт {MIN_WIN_RATE_EQUAL}%, стрик {MIN_STREAK_EQUAL}"
    )
    
    while True:
        # Прямой запрос к живому фиду настольного тенниса на Livesport.cz
        feed = make_request("https://d.livesport.cz/x/feed/l_3_2_ru-ru_1")
        
        if feed:
            print("[Livesport] Данные успешно получены. Начинаем парсинг...")
            live_matches = parse_flashscore_live(feed)
            print(f"[Livesport] Найдено матчей для анализа: {len(live_matches)}")
            
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
                
                # Стратегия 1: Камбэк фаворита (проигрывает по сетам)
                if home_stats["win_rate"] >= MIN_WIN_RATE_FAV and home_stats["streak"] >= MIN_STREAK_FAV and home_score < away_score:
                    msg = (
                        f"🔥 <b>СТРАТЕГИЯ: Камбэк фаворита (Livesport)</b>\n"
                        f"🏆 {m['tournament'].upper()}\n\n"
                        f"👤 <b>{home_team}</b> (Винрейт: {home_stats['win_rate']}% | Стрик: {home_stats['streak']})\n"
                        f"Форма: {home_stats['symbols']}\n\n"
                        f"👤 <b>{away_team}</b> (Винрейт: {away_stats['win_rate']}% | Стрик: {away_stats['streak']})\n"
                        f"Форма: {away_stats['symbols']}\n\n"
                        f"📊 <b>Текущий счет по сетам:</b> {home_score} : {away_score}"
                    )
                    send_telegram_message(msg)
                    SENT_SIGNALS.add(match_id)
                    
                elif away_stats["win_rate"] >= MIN_WIN_RATE_FAV and away_stats["streak"] >= MIN_STREAK_FAV and away_score < home_score:
                    msg = (
                        f"🔥 <b>СТРАТЕГИЯ: Камбэк фаворита (Livesport)</b>\n"
                        f"🏆 {m['tournament'].upper()}\n\n"
                        f"👤 <b>{away_team}</b> (Винрейт: {away_stats['win_rate']}% | Стрик: {away_stats['streak']})\n"
                        f"Форма: {away_stats['symbols']}\n\n"
                        f"👤 <b>{home_team}</b> (Винрейт: {home_stats['win_rate']}% | Стрик: {home_stats['streak']})\n"
                        f"Форма: {home_stats['symbols']}\n\n"
                        f"📊 <b>Текущий счет по сетам:</b> {home_score} : {away_score}"
                    )
                    send_telegram_message(msg)
                    SENT_SIGNALS.add(match_id)
                
                # Стратегия 2: Равная игра ТОП игроков
                elif home_stats["win_rate"] >= MIN_WIN_RATE_EQUAL and away_stats["win_rate"] >= MIN_WIN_RATE_EQUAL:
                    if home_stats["streak"] >= MIN_STREAK_EQUAL and away_stats["streak"] >= MIN_STREAK_EQUAL:
                        msg = (
                            f"⚔️ <b>СТРАТЕГИЯ: Равная игра ТОП (Livesport)</b>\n"
                            f"🏆 {m['tournament'].upper()}\n\n"
                            f"👤 {home_team} (Винрейт: {home_stats['win_rate']}% | Стрик: {home_stats['streak']})\n"
                            f"Форма: {home_stats['symbols']}\n"
                            f"👤 {away_team} (Винрейт: {away_stats['win_rate']}% | Стрик: {away_stats['streak']})\n"
                            f"Форма: {away_stats['symbols']}\n\n"
                            f"📊 Счет по сетам: {home_score} : {away_score}"
                        )
                        send_telegram_message(msg)
                        SENT_SIGNALS.add(match_id)
        else:
            print("[Livesport] Ошибка: Не удалось получить фид данных через прокси.")
            
        time.sleep(50)

# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.before_request
def start_monitoring():
    if not any(t.name == "LivesportMonitorThread" for t in threading.enumerate()):
        threading.Thread(target=monitor_table_tennis, name="LivesportMonitorThread", daemon=True).start()

@app.route('/')
def home():
    return "Бот активен на Livesport.cz с прокси!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
