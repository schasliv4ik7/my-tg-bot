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

# Реалистичные User-Agent для обхода Cloudflare на основной странице
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edge/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
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
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.aiscore.com/",
        "Cache-Control": "max-age=0",
        "Upgrade-Insecure-Requests": "1"
    }
    try:
        print(f"[AiScore PC] Отправка запроса на {url}...")
        response = session.get(url, headers=headers, timeout=15, verify=False)
        print(f"[AiScore PC] Статус ответа сервера: {response.status_code}")
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"[AiScore PC] Исключение при выполнении запроса: {e}")
        return None

def parse_aiscore_live(html_text):
    if not html_text:
        return []
        
    matches = []
    
    # Рекурсивный поиск списков матчей в любом JSON-объекте
    def find_matches_in_json(data):
        if isinstance(data, dict):
            # Проверяем, похож ли этот словарь на объект матча
            if "homeName" in data or "homeTeamName" in data or "homeTeam" in data:
                # Проверим, относится ли он к настольному теннису
                tour_name = str(data.get("tournamentName", data.get("compName", ""))).lower()
                if any(t in tour_name for t in ALLOWED_TOURNAMENTS):
                    return [data]
            
            results = []
            for k, v in data.items():
                res = find_matches_in_json(v)
                if res:
                    results.extend(res)
            return results
            
        elif isinstance(data, list):
            results = []
            for item in data:
                res = find_matches_in_json(item)
                if res:
                    results.extend(res)
            return results
        return []

    # Находим абсолютно все блоки скриптов на странице
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html_text, re.DOTALL)
    print(f"[AiScore PC] Найдено скриптов на странице для анализа: {len(scripts)}")
    
    for idx, script_content in enumerate(scripts):
        # Ищем потенциальные JSON структуры внутри скрипта
        json_candidates = re.findall(r'({.*?})', script_content, re.DOTALL)
        for candidate in json_candidates:
            # Ограничиваем длину кандидата, чтобы не парсить слишком мелкий мусор
            if len(candidate) < 150:
                continue
            try:
                parsed_json = json.loads(candidate)
                found_raw = find_matches_in_json(parsed_json)
                if found_raw:
                    print(f"[AiScore PC] В скрипте #{idx} обнаружена рабочая структура данных с матчами!")
                    for m in found_raw:
                        tournament_name = str(m.get("tournamentName", m.get("compName", m.get("tournament", "Unknown")))).lower()
                        status = str(m.get("status", m.get("statusId", "")))
                        
                        # Собираем данные матча (в лайве он или нет)
                        if status == "2" or m.get("isLive", False) or m.get("live", False):
                            home_team = m.get("homeName", m.get("homeTeamName", m.get("homeTeam", {}).get("name", "Игрок 1")))
                            away_team = m.get("awayName", m.get("awayTeamName", m.get("awayTeam", {}).get("name", "Игрок 2")))
                            
                            # Безопасное извлечение счета
                            home_score = int(m.get("homeScore", m.get("homeSetScore", m.get("homeScoreTotal", 0))))
                            away_score = int(m.get("awayScore", m.get("awaySetScore", m.get("awayScoreTotal", 0))))
                            
                            match_info = {
                                "id": str(m.get("id", m.get("matchId", random.randint(100000, 999999)))),
                                "tournament": tournament_name,
                                "home": home_team,
                                "away": away_team,
                                "home_score": home_score,
                                "away_score": away_score
                            }
                            # Исключаем дубликаты по ID
                            if not any(parsed_m["id"] == match_info["id"] for parsed_m in matches):
                                matches.append(match_info)
                                print(f"[AiScore PC] Добавлен матч: {home_team} vs {away_team} ({tournament_name}) — {home_score}:{away_score}")
            except:
                continue

    return matches

def get_player_history_stats(player_name):
    # Генерация мок-статистики для тестирования логики
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
    send_telegram_message("🤖 <b>Бот успешно запущен на супер-парсере HTML AiScore!</b>")
    
    while True:
        try:
            html = make_request("https://www.aiscore.com/ru/table-tennis")
            if html:
                live_matches = parse_aiscore_live(html)
                print(f"[Мониторинг] Отобрано {len(live_matches)} матчей для анализа стратегий.")
                
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
                            f"🎯 <b>СТРАТЕГИЯ: Упущенный 1-й сет (AiScore PC)</b>\n"
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
                            f"🎯 <b>СТРАТЕГИЯ: Упущенный 1-й сет (AiScore PC)</b>\n"
                            f"🏆 {m['tournament'].upper()}\n\n"
                            f"🟢 <b>Рекомендуемая ставка: П2 (Победа {away_team})</b>\n\n"
                            f"👤 {away_team} | {away_stats['win_rate']}% | Форма: {away_stats['symbols']}\n"
                            f"👤 {home_team} | {home_stats['win_rate']}% | Форма: {home_stats['symbols']}\n\n"
                            f"📊 <b>Текущий счет:</b> {home_score} : {away_score}"
                        )
                        send_telegram_message(msg)
                        SENT_SIGNALS.add(match_id)
            else:
                print("[Мониторинг] Не удалось получить HTML страницы.")
        except Exception as e:
            print(f"[Мониторинг] Ошибка в главном цикле: {e}")
            
        time.sleep(40)

# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот активен и парсит AiScore с глубоким анализом скриптов!"

monitor_thread = threading.Thread(target=monitor_table_tennis, name="AiScorePCMonitorThread", daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
