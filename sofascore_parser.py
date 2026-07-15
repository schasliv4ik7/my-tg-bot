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

# --- БЕЛЫЙ СПИСОК ТУРНИРОВ ---
ALLOWED_TOURNAMENTS = ["liga pro", "setka cup", "tt cup"]

# --- НАСТРОЙКИ ДЛЯ СУПЕР-СИГНАЛА (Камбэк фаворита) ---
MIN_WIN_RATE_FAV = 70.0
MIN_STREAK_FAV = 3

# --- НАСТРОЙКИ ДЛЯ СИГНАЛА "РАВНАЯ ИГРА" ---
MIN_WIN_RATE_EQUAL = 55.0
MIN_STREAK_EQUAL = 2

# Заголовки для имитации браузера
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "Cache-Control": "no-cache"
}

# Отключение проверки SSL
SSL_CONTEXT = ssl._create_unverified_context()

# Множество для отправленных сигналов
SENT_SIGNALS = set()


def send_telegram_message(text):
    """Отправляет форматированное сообщение в Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": YOUR_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        # Кодируем данные в формат JSON и добавляем правильный заголовок контента
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json"}, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
            if response.status != 200:
                print(f"[Telegram] Ошибка отправки: {response.status}")
    except Exception as e:
        print(f"[Telegram] Ошибка подключения: {e}")

def parse_fractional_odds(fraction_str):
    """Преобразует дробный коэффициент в десятичный (float)."""
    if not fraction_str or "/" not in fraction_str:
        return None
    try:
        num, denom = fraction_str.split("/")
        decimal_odds = (int(num) / int(denom)) + 1
        return round(decimal_odds, 2)
    except Exception:
        return None


def make_request(url, silent_404=False):
    """Безопасный запрос к API Sofascore."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
            return None
    except HTTPError as e:
        if e.code == 404 and silent_404:
            return None
        print(f"[Ошибка запроса]: HTTP Error {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"[Ошибка сетевого запроса]: {e}")
        return None


def get_live_table_tennis_matches():
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    data = make_request(url)
    return data.get("events", []) if data else []


def get_match_odds(event_id):
    """Возвращает предматчевые и текущие коэффициенты."""
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/odds/1/all"
    odds_data = make_request(url, silent_404=True)
    
    if odds_data:
        markets = odds_data.get("markets", [])
        for market in markets:
            if market.get("marketName") in ["Match winner", "Full time"]:
                choices = market.get("choices", [])
                if len(choices) >= 2:
                    p1_init_frac = choices[0].get("initialFractionalValue")
                    p2_init_frac = choices[1].get("initialFractionalValue")
                    p1_live_frac = choices[0].get("fractionalValue")
                    p2_live_frac = choices[1].get("fractionalValue")
                    
                    return {
                        "П1_старт": parse_fractional_odds(p1_init_frac),
                        "П2_старт": parse_fractional_odds(p2_init_frac),
                        "П1_лайв": parse_fractional_odds(p1_live_frac),
                        "П2_лайв": parse_fractional_odds(p2_live_frac)
                    }
    return None


def get_player_stats(match_id, side):
    """Анализирует последние 5 матчей игрока."""
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
        
        if target_player_id == home_id:
            won = home_score > away_score
        else:
            won = away_score > home_score
            
        wins.append(won)
        
    if not wins:
        return {"symbols": "Нет данных", "win_rate": 0.0, "streak": 0}
        
    win_rate = (wins.count(True) / len(wins)) * 100
    
    streak = 0
    for w in wins:
        if w:
            streak += 1
        else:
            break
            
    symbols = "".join(["🟢" if w else "🔴" for w in wins])
    
    return {"symbols": symbols, "win_rate": round(win_rate, 1), "streak": streak}


def is_tournament_allowed(tournament_name):
    if not tournament_name:
        return False
    name_lower = tournament_name.lower()
    return any(allowed in name_lower for allowed in ALLOWED_TOURNAMENTS)


def monitor_table_tennis():
    print("=== Двухуровневый фильтр сигналов запущен ===")
    send_telegram_message(
        f"🤖 <b>Двухуровневый фильтр успешно запущен на Render!</b>\n"
        f"1️⃣ <b>Камбэк фаворита:</b> винрейт {MIN_WIN_RATE_FAV}%, стрик {MIN_STREAK_FAV}\n"
        f"2️⃣ <b>Равная игра ТОП:</b> винрейт {MIN_WIN_RATE_EQUAL}%, стрик {MIN_STREAK_EQUAL}"
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
                    if not odds or not isinstance(odds, dict):
                        continue
                    
                    p1_start = odds.get("П1_старт")
                    p2_start = odds.get("П2_старт")
                    p1_live = odds.get("П1_лайв")
                    p2_live = odds.get("П2_live_frac") or odds.get("П2_лайв")
                    
                    if not all([p1_start, p2_start, p1_live, p2_live]):
                        continue
                    
                    home_score = int(match.get("homeScore", {}).get("display", 0))
                    away_score = int(match.get("awayScore", {}).get("display", 0))
                    home_player = match.get("homeTeam", {}).get("name", "Player 1")
                    away_player = match.get("awayTeam", {}).get("name", "Player 2")
                    
                    signal_triggered = False
                    msg_text = ""
                    
                    # --- СЦЕНАРИЙ 1: КАМБЭК ТОП-ФАВОРИТА (Игрок 1) ---
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
                                f"📊 <b>Коэффициенты:</b>\n"
                                f"• Старт П1: <code>{p1_start}</code> | <b>Лайв П1: <code>{p1_live}</code></b> 👈\n\n"
                                f"📈 <b>Аналитика фаворита ({home_player}):</b>\n"
                                f"• Последние матчи: {stats['symbols']}\n"
                                f"• Процент побед: <b>{stats['win_rate']}%</b>\n"
                                f"• Серия побед: <b>{stats['streak']}</b>\n\n"
                                f"👤 <b>Соперник ({away_player}):</b> {opp_stats['symbols']}"
                            )
                    
                    # --- СЦЕНАРИЙ 1: КАМБЭК ТОП-ФАВОРИТА (Игрок 2) ---
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
                                f"📊 <b>Коэффициенты:</b>\n"
                                f"• Старт П2: <code>{p2_start}</code> | <b>Лайв П2: <code>{p2_live}</code></b> 👈\n\n"
                                f"📈 <b>Аналитика фаворита ({away_player}):</b>\n"
                                f"• Последние матчи: {stats['symbols']}\n"
                                f"• Процент побед: <b>{stats['win_rate']}%</b>\n"
                                f"• Серия побед: <b>{stats['streak']}</b>\n\n"
                                f"👤 <b>Соперник ({home_player}):</b> {opp_stats['symbols']}"
                            )
                    
                    # --- СЦЕНАРИЙ 2: РАВНАЯ ИГРА ТОПОВ (Счет 1:1 по сетам) ---
                    if not signal_triggered and (home_score == 1 and away_score == 1):
                        p1_stats = get_player_stats(event_id, "home")
                        p2_stats = get_player_stats(event_id, "away")
                        
                        if p1_stats["win_rate"] >= MIN_WIN_RATE_EQUAL and p1_stats["streak"] >= MIN_STREAK_EQUAL and 1.85 <= p1_live <= 2.20:
                            signal_triggered = True
                            msg_text = (
                                f"⚡ <b>СИГНАЛ: Равная игра ТОП-игроков!</b>\n\n"
                                f"🏆 {tournament_name}\n"
                                f"⚔️ <b>{home_player}</b> vs {away_player}\n"
                                f"📈 Счет по сетам: <b>1 : 1</b>\n\n"
                                f"📊 <b>Коэффициенты:</b>\n"
                                f"• <b>Лайв П1: <code>{p1_live}</code></b> 👈\n\n"
                                f"📈 <b>Аналитика ({home_player}):</b>\n"
                                f"• Форма: {p1_stats['symbols']} (Винрейт: {p1_stats['win_rate']}%, Стрик: {p1_stats['streak']})\n\n"
                                f"👤 <b>Соперник ({away_player}):</b>\n"
                                f"• Форма: {p2_stats['symbols']} (Винрейт: {p2_stats['win_rate']}%)"
                            )
                        
                        elif p2_stats["win_rate"] >= MIN_WIN_RATE_EQUAL and p2_stats["streak"] >= MIN_STREAK_EQUAL and 1.85 <= p2_live <= 2.20:
                            signal_triggered = True
                            msg_text = (
                                f"⚡ <b>СИГНАЛ: Равная игра ТОП-игроков!</b>\n\n"
                                f"🏆 {tournament_name}\n"
                                f"⚔️ {home_player} vs <b>{away_player}</b>\n"
                                f"📈 Счет по сетам: <b>1 : 1</b>\n\n"
                                f"📊 <b>Коэффициенты:</b>\n"
                                f"• <b>Лайв П2: <code>{p2_live}</code></b> 👈\n\n"
                                f"📈 <b>Аналитика ({away_player}):</b>\n"
                                f"• Форма: {p2_stats['symbols']} (Винрейт: {p2_stats['win_rate']}%, Стрик: {p2_stats['streak']})\n\n"
                                f"👤 <b>Соперник ({home_player}):</b>\n"
                                f"• Форма: {p1_stats['symbols']} (Винрейт: {p1_stats['win_rate']}%)"
                            )
                    
                    if signal_triggered:
                        print(f"[ОТПРАВЛЕНО] {home_player} - {away_player} ({tournament_name})")
                        send_telegram_message(msg_text)
                        SENT_SIGNALS.add(event_id)
                    
                    time.sleep(1.5)
                
                expired_matches = SENT_SIGNALS - current_live_ids
                for expired_id in expired_matches:
                    SENT_SIGNALS.remove(expired_id)
            else:
                print("Сейчас нет активных лайв-матчей.")
                
        except Exception as e:
            print(f"[Фоновая ошибка мониторинга]: {e}")
            
        print("Сканирование завершено. Ожидание 30 сек...")
        time.sleep(30)


# --- МИКРО-ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот активен, веб-порт открыт, сканирование идет 24/7!"

if __name__ == "__main__":
    # Запуск логики парсера в отдельном независимом потоке
    threading.Thread(target=monitor_table_tennis, daemon=True).start()
    
    # Запуск веб-сервера Flask на динамическом порту Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
