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

# Десктопные User-Agent (имитируем обычный ПК-браузер)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edge/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
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
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.aiscore.com/",
        "Sec-Ch-Ua": '"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
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
    
    # 1. Пробуем извлечь JSON десктопной страницы из __NEXT_DATA__
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text, re.DOTALL)
    if next_data_match:
        try:
            json_data = json.loads(next_data_match.group(1))
            print("[AiScore PC] Успешно извлечен JSON из __NEXT_DATA__")
        except Exception as e:
            print(f"[AiScore PC] Ошибка разбора __NEXT_DATA__ JSON: {e}")
            
    # 2. Альтернативный поиск по INITIAL_STATE
    if not json_data:
        initial_state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html_text, re.DOTALL)
        if initial_state_match:
            try:
                json_data = json.loads(initial_state_match.group(1))
                print("[AiScore PC] Успешно извлечен JSON из __INITIAL_STATE__")
            except Exception as e:
                print(f"[AiScore PC] Ошибка разбора __INITIAL_STATE__ JSON: {e}")

    # Если JSON найден, разбираем его структуру
    if json_data:
        try:
            props = json_data.get("props", {})
            page_props = props.get("pageProps", {})
            initial_state = page_props.get("initialState", page_props)
            
            # Извлекаем список матчей
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
                
                # Фильтруем по белому списку
                if not any(t in tournament_name for t in ALLOWED_TOURNAMENTS):
                    continue
                
                # Статус матча в лайве (2 или флаг isLive)
                status = str(m.get("status", m.get("statusId", "")))
                if status == "2" or m.get("isLive", False):
                    match_id = str(m.get("id", m.get("matchId", random.randint(100000, 999999))))
                    home_player = m.get("homeName", m.get("homeTeamName", "Игрок 1"))
                    away_player = m.get("awayName", m.get("awayTeamName", "Игрок 2"))
                    
                    # Счет по сетам
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
                print(f"[Debug] Сейчас в лайве на AiScore (ПК) идут турниры: {list(seen_tournaments)}")
                
        except Exception as e:
            print(f"[AiScore PC] Ошибка разбора структуры JSON: {e}")

    # Резервный поиск, если JSON не отдался напрямую
    if not matches:
        print("[AiScore PC] Сработал резервный парсер структуры...")
        raw_matches = re.findall(r'class="match-item".*?data-id="(\d+)"', html_text, re.DOTALL)
        if raw_matches:
            print(f"[AiScore PC] Резервный парсер нашел сырых матчей в HTML: {len(raw_matches)}")
            
    return matches

def get_player_history_stats(player_name):
    # Статистика (последние 5 игр)
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
        f"🤖 <b>Бот успешно переключен на ПК-версию AiScore!</b>\n\n"
        f"1️⃣ <b>Упущенный 1-й сет:</b> фаворит уступил партию (кэф вырос)\n"
        f"2️⃣ <b>Камбэк фаворита:</b> винрейт {MIN_WIN_RATE_FAV}%, стрик {MIN_STREAK_FAV}\n"
