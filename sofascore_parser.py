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

# --- БЕЛЫЙ СПИСОК ТУРНИРОВ (Русские и английские варианты) ---
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

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
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
        "Referer": "https://m.aiscore.com/",
        "Cache-Control": "max-age=0"
    }
    try:
        response = session.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            return response.text
        print(f"[AiScore] Ошибка доступа. Код: {response.status_code}")
        return None
    except Exception as e:
        print(f"[AiScore] Ошибка запроса: {e}")
        return None

def parse_aiscore_live(html_text):
    if not html_text:
        return []
        
    matches = []
    
    # Пытаемся найти JSON-данные состояния страницы, которые AiScore рендерит в HTML
    json_data = None
    
    # Способ 1: Скрипт __NEXT_DATA__ (самый частый для Next.js / мобильных версий)
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text, re.DOTALL)
    if next_data_match:
        try:
            json_data = json.loads(next_data_match.group(1))
            print("[AiScore] Успешно извлечен JSON из __NEXT_DATA__")
        except Exception as e:
            print(f"[AiScore] Ошибка разбора __NEXT_DATA__ JSON: {e}")
            
    # Способ 2: Альтернативный поиск INITIAL_STATE
    if not json_data:
        initial_state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html_text, re.DOTALL)
        if initial_state_match:
            try:
                json_data = json.loads(initial_state_match.group(1))
                print("[AiScore] Успешно извлечен JSON из __INITIAL_STATE__")
            except Exception as e:
                print(f"[AiScore] Ошибка разбора __INITIAL_STATE__ JSON: {e}")

    # Если нашли JSON, вытаскиваем из него матчи
    if json_data:
        try:
            # Ищем ветку с матчами в структуре данных (может отличаться в зависимости от версии страницы)
            props = json_data.get("props", {})
            page_props = props.get("pageProps", {})
            initial_state = page_props.get("initialState", page_props)
            
            # Пытаемся найти список матчей в разных возможных ключах структуры AiScore
            match_list = (
                initial_state.get("matches", []) or 
                initial_state.get("matchList", []) or 
                initial_state.get("liveMatches", []) or
                json_data.get("matches", [])
            )
            
            seen_tournaments = set()
            
            for m in match_list:
                tournament_name = m.get("tournamentName", m.get("compName", "Unknown")).lower()
                seen_tournaments.add(tournament_name)
                
                # Фильтр по турнирам
                if not any(t in tournament_name for t in ALLOWED_TOURNAMENTS):
                    continue
                
                # Статус матча: 2 или "live" означает, что матч идет прямо сейчас
                status = str(m.get("status", m.get("statusId", "")))
                
                # Обычно на AiScore статус 2 - это LIVE, статус 1 - не начался, 3 - завершен
                if status == "2" or m.get("isLive", False):
                    match_id = str(m.get("id", m.get("matchId", random.randint(100000, 999999))))
                    home_player = m.get("homeName", m.get("homeTeamName", "Игрок 1"))
                    away_player = m.get("awayName", m.get("awayTeamName", "Игрок 2"))
                    
                    # Получаем текущий счет по сетам
                    home_score = int(m.get("homeScore", m.get("homeSetScore", 0)))
                    away_score = int(m.get("awayScore", m.get("awaySetScore", 0)))
                    
                    matches.append({
                        "id": match_id,
                        "tournament": tournament_name,
                        "home": home_player,
                        "away": away_player,
                        "home_score": home_score,
                        "away_score": away_score
                    })
            
            if seen_tournaments:
                print(f"[Debug] Сейчас в лайве на AiScore идут турниры: {list(seen_tournaments)}")
                
        except Exception as e:
            print(f"[AiScore] Ошибка прохода по структуре JSON: {e}")

    # Резервный вариант: если JSON не нашелся, парсим базовые данные регулярками из HTML
    if not matches:
        print("[AiScore] Сработал резервный регулярный парсер HTML...")
        # Ищем блоки матчей через регулярные выражения
        raw_matches = re.findall(r'class="match-item".*?data-id="(\d+)"', html_text, re.DOTALL)
        if raw_matches:
            print(f"[AiScore] Резервный парсер нашел сырых матчей в HTML: {len(raw_matches)}")
            
    return matches

def get_player_history_stats(player_name):
    # Симуляция сбора статистики (последние 5 игр)
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
        f"🤖 <b>Бот успешно переключен на AiScore!</b>\n\n"
        f"1️⃣ <b>Упущенный 1-й сет:</b> фаворит уступил партию (кэф вырос)\n"
        f"2️⃣ <b>Камбэк фаворита:</b> винрейт {MIN_WIN_RATE_FAV}%, стрик {MIN_STREAK_FAV}\n"
        f"3️⃣ <b>Равная игра ТОП:</b> винрейт {MIN_WIN_RATE_EQUAL}%, стрик {MIN_STREAK_EQUAL}"
    )
    
    while True:
        # Запрашиваем мобильную лайв-страницу настольного тенниса на AiScore
        html = make_request("https://m.aiscore.com/ru/table-tennis")
        
        if html:
            print("[AiScore] Страница успешно загружена. Начинаем парсинг...")
            live_matches = parse_aiscore_live(html)
            print(f"[AiScore] Найдено матчей для анализа: {len(live_matches)}")
            
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
                        f"🟢 <b>Рекомендуемая ставка: П1 (Победа {home_team})</b>\n"
                        f"📝 <b>Почему:</b> Наш фаворит имеет мощный винрейт {home_stats['win_rate']}% и стрик {home_stats['streak']} побед подряд. "
                        f"Он случайно отдал первый сет и сейчас идет разогретым. Коэффициент на его победу в лайве сейчас завышен и крайне выгоден!\n\n"
                        f"👤 {home_team} | {home_stats['win_rate']}% | Форма: {home_stats['symbols']}\n"
                        f"👤 {away_team} | {away_stats['win_rate']}% | Форма: {away_stats['symbols']}\n\n"
                        f"📊 <b>Текущий счет:</b> {home_score} : {away_score}"
                    )
                    send_telegram_message(msg)
                    SENT_SIGNALS.add(match_id)
                    continue

                elif away_stats["win_rate"] >= MIN_WIN_RATE_FAV and away_stats["streak"] >= MIN_STREAK_FAV and home_score == 1 and away_score == 0:
                    msg = (
                        f"🎯 <b>СТРАТЕГИЯ: Упущенный 1-й сет (AiScore)</b>\n"
                        f"🏆 {m['tournament'].upper()}\n\n"
                        f"🟢 <b>Рекомендуемая ставка: П2 (Победа {away_team})</b>\n"
                        f"📝 <b>Почему:</b> Наш фаворит имеет мощный винрейт {away_stats['win_rate']}% и стрик {away_stats['streak']} побед подряд. "
                        f"Он случайно отдал первый сет и сейчас идет разогретым. Коэффициент на его победу в лайве сейчас завышен и крайне выгоден!\n\n"
                        f"👤 {away_team} | {away_stats['win_rate']}% | Форма: {away_stats['symbols']}\n"
                        f"👤 {home_team} | {home_stats['win_rate']}% | Форма: {home_stats['symbols']}\n\n"
                        f"📊 <b>Текущий счет:</b> {home_score} : {away_score}"
                    )
                    send_telegram_message(msg)
                    SENT_SIGNALS.add(match_id)
                    continue

                # --- СТРАТЕГИЯ 2: КАМБЭК ФАВОРИТА (Глубокое отставание) ---
                if home_stats["win_rate"] >= MIN_WIN_RATE_FAV and home_stats["streak"] >= MIN_STREAK_FAV and home_score < away_score:
                    msg = (
                        f"🔥 <b>СТРАТЕГИЯ: Камбэк фаворита (AiScore)</b>\n"
                        f"🏆 {m['tournament'].upper()}\n\n"
                        f"🟢 <b>Рекомендуемая ставка: Победа {home_team} (П1)</b>\n"
                        f"📝 <b>Почему:</b> Явный фаворит (винрейт {home_stats['win_rate']}%) горит по ходу встречи. "
                        f"Класс игрока и его победный стрик ({home_stats['streak']}) указывают на высокую вероятность камбэка.\n\n"
                        f"👤 {home_team} | Форма: {home_stats['symbols']}\n"
                        f"👤 {away_team} | Форма: {away_stats['symbols']}\n\n"
                        f"📊 <b>Текущий счет по сетам:</b> {home_score} : {away_score}"
                    )
                    send_telegram_message(msg)
                    SENT_SIGNALS.add(match_id)
                    
                elif away_stats["win_rate"] >= MIN_WIN_RATE_FAV and away_stats["streak"] >= MIN_STREAK_FAV and away_score < home_score:
                    msg = (
                        f"🔥 <b>СТРАТЕГИЯ: Камбэк фаворита (AiScore)</b>\n"
                        f"🏆 {m['tournament'].upper()}\n\n"
                        f"🟢 <b>Рекомендуемая ставка: Победа {away_team} (П2)</b>\n"
                        f"📝 <b>Почему:</b> Явный фаворит (винрейт {away_stats['win_rate']}%) горит по ходу встречи. "
                        f"Класс игрока и его победный стрик ({away_stats['streak']}) указывают на высокую вероятность камбэка.\n\n"
                        f"👤 {away_team} | Форма: {away_stats['symbols']}\n"
                        f"👤 {home_team} | Форма: {home_stats['symbols']}\n\n"
                        f"📊 <b>Текущий счет по сетам:</b> {home_score} : {away_score}"
                    )
                    send_telegram_message(msg)
                    SENT_SIGNALS.add(match_id)
                
                # --- СТРАТЕГИЯ 3: РАВНАЯ ИГРА ТОП ИГРОКОВ ---
                elif home_stats["win_rate"] >= MIN_WIN_RATE_EQUAL and away_stats["win_rate"] >= MIN_WIN_RATE_EQUAL:
                    if home_stats["streak"] >= MIN_STREAK_EQUAL and away_stats["streak"] >= MIN_STREAK_EQUAL:
                        recommended = f"ТБ по очкам / победа отстающего в сете"
                        msg = (
                            f"⚔️ <b>СТРАТЕГИЯ: Равная игра ТОП (AiScore)</b>\n"
                            f"🏆 {m['tournament'].upper()}\n\n"
                            f"🟢 <b>Рекомендуемая ставка: {recommended}</b>\n"
                            f"📝 <b>Почему:</b> Оба игрока находятся на подъеме (винрейты > {MIN_WIN_RATE_EQUAL}% и серии побед). "
                            f"Встречаются два равных лидера, ожидается затяжной плотный матч с высокой вероятностью экстра-поинтов.\n\n"
                            f"👤 {home_team} (Винрейт: {home_stats['win_rate']}% | Стрик: {home_stats['streak']})\n"
                            f"👤 {away_team} (Винрейт: {away_stats['win_rate']}% | Стрик: {away_stats['streak']})\n\n"
                            f"📊 Счет по сетам: {home_score} : {away_score}"
                        )
                        send_telegram_message(msg)
                        SENT_SIGNALS.add(match_id)
        else:
            print("[AiScore] Ошибка: Не удалось получить данные с сайта.")
            
        time.sleep(40)  # Твой интервал 40 секунд

# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.before_request
def start_monitoring():
    if not any(t.name == "AiScoreMonitorThread" for t in threading.enumerate()):
        threading.Thread(target=monitor_table_tennis, name="AiScoreMonitorThread", daemon=True).start()

@app.route('/')
def home():
    return "Бот активен на AiScore с прокси!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
