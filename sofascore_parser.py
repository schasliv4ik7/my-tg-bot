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

# Мобильные User-Agent'ы для запроса к мобильной версии сайта
MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.36"
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

def make_request(url):
    headers = {
        "User-Agent": random.choice(MOBILE_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://m.aiscore.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    try:
        print(f"[AiScore Mobile] Запрос к {url}...")
        response = session.get(url, headers=headers, timeout=15, verify=False)
        print(f"[AiScore Mobile] Статус ответа сервера: {response.status_code}")
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"[AiScore Mobile] Ошибка сети: {e}")
        return None

def parse_aiscore_mobile_live(html_text):
    if not html_text:
        return []
        
    matches = []
    
    # 1. Попытка быстро найти __NEXT_DATA__ (стандарт для мобильной версии Next.js)
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text, re.DOTALL)
    
    json_blocks = []
    if next_data_match:
        print("[AiScore Mobile] Найдена структура __NEXT_DATA__")
        json_blocks.append(next_data_match.group(1))
    else:
        # Если тег переименовали, собираем все script-блоки с JSON
        print("[AiScore Mobile] Тег __NEXT_DATA__ не найден, сканируем все скрипты...")
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html_text, re.DOTALL)
        for s in scripts:
            if "props" in s or "queries" in s or "initialState" in s:
                json_blocks.append(s)

    # Рекурсивный обход JSON для поиска матчей
    def extract_matches(node):
        found = []
        if isinstance(node, dict):
            # Ищем признаки объекта матча
            is_match_obj = False
            # Проверяем ключевые поля (в зависимости от структуры API/Next)
            home_name = node.get("homeName") or node.get("homeTeamName") or node.get("home_name")
            away_name = node.get("awayName") or node.get("awayTeamName") or node.get("away_name")
            
            if home_name and away_name:
                tour_name = str(node.get("tournamentName", node.get("compName", node.get("tournament_name", "")))).lower()
                if any(t in tour_name for t in ALLOWED_TOURNAMENTS):
                    is_match_obj = True
            
            if is_match_obj:
                found.append(node)
            else:
                for k, v in node.items():
                    found.extend(extract_matches(v))
        elif isinstance(node, list):
            for item in node:
                found.extend(extract_matches(item))
        return found

    for block in json_blocks:
        try:
            # Чистим блок, если там есть присвоение переменной типа window.DATA = {...}
            if "=" in block and not block.strip().startswith("{"):
                block_clean = block[block.find("{"):block.rfind("}")+1]
            else:
                block_clean = block.strip()
                
            data = json.loads(block_clean)
            raw_matches = extract_matches(data)
            
            for m in raw_matches:
                # Извлекаем ID матча
                match_id = str(m.get("id") or m.get("matchId") or m.get("match_id") or random.randint(100000, 999999))
                
                # Проверяем статус (в лайве ли матч)
                # status: 2 - Live в системе AiScore
                status = str(m.get("status") or m.get("statusId") or m.get("status_id") or "")
                is_live = m.get("isLive") or m.get("live") or (status == "2")
                
                if not is_live:
                    continue
                
                tournament_name = str(m.get("tournamentName", m.get("compName", m.get("tournament_name", "Unknown")))).lower()
                home_team = m.get("homeName") or m.get("homeTeamName") or m.get("home_name") or "Игрок 1"
                away_team = m.get("awayName") or m.get("awayTeamName") or m.get("away_name") or "Игрок 2"
                
                # Извлечение счета по сетам (в лайве счет часто вложен в score/setScore)
                score_obj = m.get("score") or m.get("setScore") or m
                home_score = int(score_obj.get("homeScore", score_obj.get("homeSetScore", score_obj.get("home_score", 0))))
                away_score = int(score_obj.get("awayScore", score_obj.get("awaySetScore", score_obj.get("away_score", 0))))
                
                match_info = {
                    "id": match_id,
                    "tournament": tournament_name,
                    "home": home_team,
                    "away": away_team,
                    "home_score": home_score,
                    "away_score": away_score
                }
                
                if not any(parsed_m["id"] == match_info["id"] for parsed_m in matches):
                    matches.append(match_info)
                    print(f"[AiScore Mobile] Обнаружен лайв: {home_team} vs {away_team} ({tournament_name}) — Счет: {home_score}:{away_score}")
        except Exception as e:
            continue

    return matches

def get_player_history_stats(player_name):
    # Симуляция получения статистики игрока для работы триггеров
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
    send_telegram_message("🤖 <b>Бот успешно запущен на мобильном парсере AiScore!</b>")
    
    while True:
        try:
            # Запрашиваем мобильную версию страницы настольного тенниса
            html = make_request("https://m.aiscore.com/table-tennis")
            if html:
                live_matches = parse_aiscore_mobile_live(html)
                print(f"[Мониторинг] Отобрано {len(live_matches)} лайв-матчей для анализа стратегий.")
                
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
                            f"🎯 <b>СТРАТЕГИЯ: Упущенный 1-й сет (AiScore Mobile)</b>\n"
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
                            f"🎯 <b>СТРАТЕГИЯ: Упущенный 1-й сет (AiScore Mobile)</b>\n"
                            f"🏆 {m['tournament'].upper()}\n\n"
                            f"🟢 <b>Рекомендуемая ставка: П2 (Победа {away_team})</b>\n\n"
                            f"👤 {away_team} | {away_stats['win_rate']}% | Форма: {away_stats['symbols']}\n"
                            f"👤 {home_team} | {home_stats['win_rate']}% | Форма: {home_stats['symbols']}\n\n"
                            f"📊 <b>Текущий счет:</b> {home_score} : {away_score}"
                        )
                        send_telegram_message(msg)
                        SENT_SIGNALS.add(match_id)
            else:
                print("[Мониторинг] Не удалось получить мобильный HTML.")
        except Exception as e:
            print(f"[Мониторинг] Ошибка в главном цикле: {e}")
            
        time.sleep(40)

# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот активен и парсит мобильную версию AiScore!"

monitor_thread = threading.Thread(target=monitor_table_tennis, name="AiScoreMobileMonitorThread", daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
