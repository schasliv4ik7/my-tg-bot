import os
import json
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

# Список различных User-Agent для обхода блокировок
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

session = requests.Session()

if PROXY_URL:
    session.proxies = {
        "http": PROXY_URL,
        "https": PROXY_URL
    }

SENT_SIGNALS = set()


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[Telegram] Ошибка подключения: {e}")


def parse_fractional_odds(fraction_str):
    if not fraction_str or "/" not in fraction_str:
        return None
    try:
        num, denom = fraction_str.split("/")
        return round((int(num) / int(denom)) + 1, 2)
    except Exception:
        return None


def make_request(url, silent_404=False):
    """Безопасный запрос с динамической сменой заголовков и подробным логированием."""
    # Рандомизируем заголовки для каждого запроса
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    try:
        response = session.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401 or response.status_code == 407:
            print(f"[КРИТИЧЕСКАЯ ОШИБКА]: Прокси отклонил логин/пароль! Код {response.status_code}")
            return None
        elif response.status_code == 403:
            print("[Ошибка запроса]: HTTP Error 403 (Блокировка IP-адреса сайтом Sofascore)")
            return None
        elif response.status_code == 404 and silent_404:
            return None
        print(f"[Ошибка запроса]: HTTP Error {response.status_code}")
        return None
    except Exception as e:
        print(f"[Ошибка сетевого запроса]: {e}")
        return None


def get_live_table_tennis_matches():
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    data = make_request(url)
    return data.get("events", []) if data else []


def get_match_odds(event_id):
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/odds/1/all"
    odds_data = make_request(url, silent_404=True)
    if odds_data:
        markets = odds_data.get("markets", [])
        for market in markets:
            if market.get("marketName") in ["Match winner", "Full time"]:
                choices = market.get("choices", [])
                if len(choices) >= 2:
                    return {
                        "П1_старт": parse_fractional_odds(choices[0].get("initialFractionalValue")),
                        "П2_старт": parse_fractional_odds(choices[1].get("initialFractionalValue")),
                        "П1_лайв": parse_fractional_odds(choices[0].get("fractionalValue")),
                        "П2_лайв": parse_fractional_odds(choices[1].get("fractionalValue"))
                    }
    return None


def get_player_stats(match_id, side):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/team-events/{side}"
    data = make_request(url, silent_404=True)
    if not data or "events" not in data:
        return {"symbols": "Нет данных", "win_rate": 0.0, "streak": 0}
    
    events = data.get("events", [])[:5]
    wins = []
    for event in events:
        home_id = event.get("homeTeam", {}).get("id")
        away_id = event.get("awayTeam", {}).get("id")
        home_score = event.get("homeScore", {}).get("display")
        away_score = event.get("awayScore", {}).get("display")
        if home_score is None or away_score is None:
            continue
        target_player_id = home_id if side == "home" else away_id
        won = home_score > away_score if target_player_id == home_id else away_score > home_score
        wins.append(won)
        
    if not wins:
        return {"symbols": "Нет данных", "win_rate": 0.0, "streak": 0}
    win_rate = (wins.count(True) / len(wins)) * 100
    streak = 0
    for w in wins:
        if w: streak += 1
        else: break
    return {"symbols": "".join(["🟢" if w else "🔴" for w in wins]), "win_rate": round(win_rate, 1), "streak": streak}


def is_tournament_allowed(tournament_name):
    if not tournament_name:
        return False
    name_lower = tournament_name.lower()
    return any(allowed in name_lower for allowed in ALLOWED_TOURNAMENTS)


def monitor_table_tennis():
    print("=== Двухуровневый фильтр сигналов запущен ===")
    send_telegram_message(
        "🤖 <b>Двухуровневый фильтр успешно запущен на Render с динамической защитой!</b>"
    )
    
    while True:
        try:
            matches = get_live_table_tennis_matches()
            if matches:
                current_live_ids = set()
                for match in matches:
                    event_id = match.get("id")
                    current_live_ids.add(event_id)
                    if event_id in SENT_SIGNALS:
                        continue
                    
                    tournament_name = match.get("tournament", {}).get("name", "Unknown Tournament")
                    if not is_tournament_allowed(tournament_name):
                        continue
                    
                    odds = get_match_odds(event_id)
                    if not odds:
                        continue
                    
                    p1_start, p2_start = odds.get("П1_старт"), odds.get("П2_старт")
                    p1_live, p2_live = odds.get("П1_лайв"), odds.get("П2_лайв")
                    if not all([p1_start, p2_start, p1_live, p2_live]):
                        continue
                    
                    home_score = int(match.get("homeScore", {}).get("display", 0))
                    away_score = int(match.get("awayScore", {}).get("display", 0))
                    home_player = match.get("homeTeam", {}).get("name", "Player 1")
                    away_player = match.get("awayTeam", {}).get("name", "Player 2")
                    
                    signal_triggered = False
                    msg_text = ""
                    
                    # Сценарий 1: П1 камбэк
                    if 1.15 <= p1_start <= 1.38 and home_score < away_score and 1.60 <= p1_live <= 2.30:
                        stats = get_player_stats(event_id, "home")
                        opp_stats = get_player_stats(event_id, "away")
                        if stats["win_rate"] >= MIN_WIN_RATE_FAV and stats["streak"] >= MIN_STREAK_FAV:
                            signal_triggered = True
                            msg_text = (
                                f"🔥 <b>СУПЕР-СИГНАЛ: Камбэк ТОП-фаворита!</b>\n\n"
                                f"🏆 {tournament_name}\n"
                                f"⚔️ <b>{home_player}</b> vs {away_player}\n"
                                f"📈 Счет по сетам: <b>{home_score} : {away_score}</b>\n\n"
                                f"📊 Коэффициенты:\n• Старт П1: {p1_start} | <b>Лайв П1: {p1_live}</b>\n\n"
                                f"📈 Аналитика П1 ({home_player}):\n• Форма: {stats['symbols']} ({stats['win_rate']}%)\n"
                                f"• Стрик: {stats['streak']}\n\n"
                                f"👤 Оппонент: {opp_stats['symbols']}"
                            )
                    
                    # Сценарий 1: П2 камбэк
                    elif 1.15 <= p2_start <= 1.38 and away_score < home_score and 1.60 <= p2_live <= 2.30:
                        stats = get_player_stats(event_id, "away")
                        opp_stats = get_player_stats(event_id, "home")
                        if stats["win_rate"] >= MIN_WIN_RATE_FAV and stats["streak"] >= MIN_STREAK_FAV:
                            signal_triggered = True
                            msg_text = (
                                f"🔥 <b>СУПЕР-СИГНАЛ: Камбэк ТОП-фаворита!</b>\n\n"
                                f"🏆 {tournament_name}\n"
                                f"⚔️ {home_player} vs <b>{away_player}</b>\n"
                                f"📈 Счет по сетам: <b>{home_score} : {away_score}</b>\n\n"
                                f"📊 Коэффициенты:\n• Старт П2: {p2_start} | <b>Лайв П2: {p2_live}</b>\n\n"
                                f"📈 Аналитика П2 ({away_player}):\n• Форма: {stats['symbols']} ({stats['win_rate']}%)\n"
                                f"• Стрик: {stats['streak']}\n\n"
                                f"👤 Оппонент: {opp_stats['symbols']}"
                            )
                    
                    # Сценарий 2: Равная игра
                    if not signal_triggered and (home_score == 1 and away_score == 1):
                        p1_stats = get_player_stats(event_id, "home")
                        p2_stats = get_player_stats(event_id, "away")
                        
                        if p1_stats["win_rate"] >= MIN_WIN_RATE_EQUAL and p1_stats["streak"] >= MIN_STREAK_EQUAL and 1.85 <= p1_live <= 2.20:
                            signal_triggered = True
                            msg_text = (
                                f"⚡ <b>СИГНАЛ: Равная игра ТОП-игроков!</b>\n\n"
                                f"🏆 {tournament_name}\n"
                                f"⚔️ <b>{home_player}</b> vs {away_player}\n"
                                f"📈 Коэффициент П1: {p1_live}\n\n"
                                f"📈 Аналитика П1: {p1_stats['symbols']} ({p1_stats['win_rate']}%)\n"
                                f"👤 Оппонент: {p2_stats['symbols']}"
                            )
                        elif p2_stats["win_rate"] >= MIN_WIN_RATE_EQUAL and p2_stats["streak"] >= MIN_STREAK_EQUAL and 1.85 <= p2_live <= 2.20:
                            signal_triggered = True
                            msg_text = (
                                f"⚡ <b>СИГНАЛ: Равная игра ТОП-игроков!</b>\n\n"
                                f"🏆 {tournament_name}\n"
                                f"⚔️ {home_player} vs <b>{away_player}</b>\n"
                                f"📈 Коэффициент П2: {p2_live}\n\n"
                                f"📈 Аналитика П2: {p2_stats['symbols']} ({p2_stats['win_rate']}%)\n"
                                f"👤 Оппонент: {p1_stats['symbols']}"
                            )
                    
                    if signal_triggered:
                        print(f"[ОТПРАВЛЕНО] {home_player} - {away_player}")
                        send_telegram_message(msg_text)
                        SENT_SIGNALS.add(event_id)
                    time.sleep(2.0) # Увеличили задержку между запросами к матчам
                
                for expired_id in (SENT_SIGNALS - current_live_ids):
                    SENT_SIGNALS.remove(expired_id)
            else:
                print("Сейчас нет активных лайв-матчей.")
        except Exception as e:
            print(f"[Фоновая ошибка мониторинга]: {e}")
            
        print("Сканирование завершено. Ожидание 45 сек...")
        time.sleep(45) # Увеличили общий кулдаун, чтобы не спамить прокси


# --- МИКРО-ВЕБ-СЕРВЕР ---
app = Flask(__name__)

@app.before_request
def start_monitoring_thread():
    for thread in threading.enumerate():
        if thread.name == "SofascoreMonitorThread":
            return
    monitor_thread = threading.Thread(target=monitor_table_tennis, name="SofascoreMonitorThread", daemon=True)
    monitor_thread.start()

@app.route('/')
def home():
    return "Бот активен, веб-порт открыт, сканирование идет 24/7!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
