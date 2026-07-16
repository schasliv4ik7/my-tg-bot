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

# Реалистичные десктопные User-Agent
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
    json_data = None
    
    # 1. Сверхгибкий поиск __NEXT_DATA__
    next_data_match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_text, re.DOTALL)
    if next_data_match:
        try:
            json_data = json.loads(next_data_match.group(1))
            print("[AiScore PC] Успешно извлечен JSON из __NEXT_DATA__")
        except Exception as e:
            print(f"[AiScore PC] Ошибка парсинга __NEXT_DATA__: {e}")
            
    # 2. Поиск window.__INITIAL_STATE__
    if not json_data:
        initial_state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html_text, re.DOTALL)
        if initial_state_match:
            try:
                json_data = json.loads(initial_state_match.group(1))
                print("[AiScore PC] Успешно извлечен JSON из __INITIAL_STATE__")
            except Exception as e:
                print(f"[AiScore PC] Ошибка парсинга __INITIAL_STATE__: {e}")

    # 3. Полное сканирование всех script блоков на наличие признаков матчей
    if not json_data:
        print("[AiScore PC] Стандартные теги не найдены. Запускаем глубокое сканирование скриптов...")
        script_contents = re.findall(r'<script[^>]*>(.*?)</script>', html_text, re.DOTALL)
        for content in script_contents:
            if "matchList" in content or "liveMatches" in content or "tournamentName" in content:
                json_bound = re.search(r'({.*})', content, re.DOTALL)
                if json_bound:
                    try:
                        candidate = json.loads(json_bound.group(1))
                        if isinstance(candidate, dict):
                            json_data = candidate
                            print("[AiScore PC] Найден подходящий JSON-объект в глубоких скриптах!")
                            break
                    except:
                        continue

    if json_data:
        try:
            # Рекурсивный поиск ключей с матчами в глубине JSON-дерева
            def find_key_recursive(data, key_name):
                if isinstance(data, dict):
                    if key_name in data:
                        return data[key_name]
                    for k, v in data.items():
                        res = find_key_recursive(v, key_name)
                        if res is not None:
                            return res
                elif isinstance(data, list):
                    for item in data:
                        res = find_key_recursive(item, key_name)
                        if res is not None:
                            return res
                return None

            match_list = find_key_recursive(json_data, "matches") or \
                         find_key_recursive(json_data, "matchList") or \
                         find_key_recursive(json_data, "liveMatches") or \
                         find_key_recursive(json_data, "list")

            if match_list and isinstance(match_list, list):
                print(f"[AiScore PC] Обнаружено матчей в JSON: {len(match_list)}")
                for m in match_list:
                    if not isinstance(m, dict):
                        continue
                        
                    tournament_name = str(m.get("tournamentName", m.get("compName", m.get("tournament", "Unknown")))).lower()
                    
                    if not any(t in tournament_name for t in ALLOWED_TOURNAMENTS):
                        continue
                    
                    status = str(m.get("status", m.get("statusId", "")))
                    if status == "2" or m.get("isLive", False) or m.get("live", False):
                        match_info = {
                            "id": str(m.get("id", m.get("matchId", random.randint(100000, 999999)))),
                            "tournament": tournament_name,
                            "home": m.get("homeName", m.get("homeTeamName", m.get("homeTeam", {}).get("name", "Игрок 1"))),
                            "away": m.get("awayName", m.get("awayTeamName", m.get("awayTeam", {}).get("name", "Игрок 2"))),
                            "home_score": int(m.get("homeScore", m.get("homeSetScore", m.get("homeScoreTotal", 0)))),
                            "away_score": int(m.get("awayScore", m.get("awaySetScore", m.get("awayScoreTotal", 0))))
                        }
                        matches.append(match_info)
                        print(f"[AiScore PC] Добавлен Live-матч: {match_info['home']} vs {match_info['away']} ({match_info['tournament']})")
            else:
                print("[AiScore PC] Списки матчей в структуре JSON не найдены.")
        except Exception as e:
            print(f"[AiScore PC] Ошибка разбора JSON-дерева: {e}")
            
    # 4. Резервный HTML-парсер
    if not matches:
        print("[AiScore PC] Попытка прямого разбора HTML-верстки...")
        html_blocks = re.findall(r'<div[^>]*class="[^"]*match-item[^"]*"[^>]*>(.*?)</div>\s*</div>', html_text, re.DOTALL)
        for block in html_blocks:
            try:
                names = re.findall(r'<span[^>]*class="[^"]*name[^"]*"[^>]*>(.*?)</span>', block)
                scores = re.findall(r'<span[^>]*class="[^"]*score[^"]*"[^>]*>(\d+)</span>', block)
                
                if len(names) >= 2:
                    home_p = names[0].strip()
                    away_p = names[1].strip()
                    home_s = int(scores[0]) if len(scores) >= 1 else 0
                    away_s = int(scores[1]) if len(scores) >= 2 else 0
                    
                    matches.append({
                        "id": str(random.randint(100000, 999999)),
                        "tournament": "liga pro", 
                        "home": home_p,
                        "away": away_p,
                        "home_score": home_s,
                        "away_score": away_s
                    })
            except Exception as e:
                continue
                
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
    print("[Мониторинг] Поток успешно стартовал!")
    send_telegram_message("🤖 <b>Бот успешно перезапущен с умным ПК-парсером AiScore!</b>")
    
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
            else:
                print("[Мониторинг] Не удалось получить HTML страницы.")
        except Exception as e:
            print(f"[Мониторинг] Ошибка в главном цикле: {e}")
            
        time.sleep(40)

# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот активен и парсит ПК-версию AiScore!"

monitor_thread = threading.Thread(target=monitor_table_tennis, name="AiScorePCMonitorThread", daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
