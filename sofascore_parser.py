import json
import urllib.request
import urllib.parse
import time
import ssl
import threading
import os
import cloudscraper  # <-- Обход 403 / Cloudflare
from flask import Flask

# --- НАСТРОЙКИ TELEGRAM ---
BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

# --- ПУЛ ПРОКСИ WEBSHARE (АВТО-РОТАЦИЯ) ---
PROXIES_LIST = [
    "31.59.20.176:6754:aeeufstt:mmzjzap1e8nc",
    "31.56.127.193:7684:aeeufstt:mmzjzap1e8nc",
    "45.38.107.97:6014:aeeufstt:mmzjzap1e8nc",
    "198.105.121.200:6462:aeeufstt:mmzjzap1e8nc",
    "64.137.96.74:6641:aeeufstt:mmzjzap1e8nc",
    "198.23.243.226:6361:aeeufstt:mmzjzap1e8nc",
    "38.154.185.97:6370:aeeufstt:mmzjzap1e8nc",
    "84.247.60.125:6095:aeeufstt:mmzjzap1e8nc",
    "142.111.67.146:5611:aeeufstt:mmzjzap1e8nc",
    "191.96.254.138:6185:aeeufstt:mmzjzap1e8nc"
][span_4](start_span)[span_4](end_span)

current_proxy_index = 0

# --- БЕЛЫЙ СПИСОК ТУРНИРОВ ---
ALLOWED_TOURNAMENTS = [
    "liga pro", "лига про", 
    "setka cup", "сетка кап", "кубок сетка", 
    "tt cup", "тт кап", "тт кубок", 
    "challenger series", "челленджер", "challenger"
][span_5](start_span)[span_5](end_span)

# --- НАСТРОЙКИ СИГНАЛОВ ---
MIN_WIN_RATE_FAV = 70.0[span_6](start_span)[span_6](end_span)
MIN_STREAK_FAV = 3[span_7](start_span)[span_7](end_span)

MIN_WIN_RATE_EQUAL = 55.0[span_8](start_span)[span_8](end_span)
MIN_STREAK_EQUAL = 2[span_9](start_span)[span_9](end_span)

# Отключение проверки SSL для Telegram-запросов
SSL_CONTEXT = ssl._create_unverified_context()[span_10](start_span)[span_10](end_span)

# Множество для отправленных сигналов
SENT_SIGNALS = set()[span_11](start_span)[span_11](end_span)

# Создаем умный сканер
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)[span_12](start_span)[span_12](end_span)


def get_current_proxies_dict():
    """Формирует словарь прокси для текущего индекса."""
    global current_proxy_index
    raw_proxy = PROXIES_LIST[current_proxy_index][span_13](start_span)[span_13](end_span)
    try:
        ip, port, user, password = raw_proxy.split(":")[span_14](start_span)[span_14](end_span)
        proxy_address = f"{user}:{password}@{ip}:{port}"
        return {
            "http": f"http://{proxy_address}",
            "https": f"http://{proxy_address}"
        }, f"{ip}:{port}"
    except Exception:
        return None, "Ошибка формата"


def rotate_proxy():
    """Переключает на следующий прокси в списке."""
    global current_proxy_index
    current_proxy_index = (current_proxy_index + 1) % len(PROXIES_LIST)[span_15](start_span)[span_15](end_span)
    _, addr = get_current_proxies_dict()
    print(f"🔄 Смена прокси! Пробуем адрес: {addr}", flush=True)


def send_telegram_message(text):
    """Отправляет форматированное сообщение в Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage[span_16](start_span)"[span_16](end_span)
    payload = {
        "chat_id": YOUR_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }[span_17](start_span)[span_17](end_span)
    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")[span_18](start_span)[span_18](end_span)
        req = urllib.request.Request(url, data=data, method="POST")[span_19](start_span)[span_19](end_span)
        with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
            if response.status != 200:
                print(f"[Telegram] Ошибка отправки: {response.status}", flush=True)[span_20](start_span)[span_20](end_span)
    except Exception as e:
        print(f"[Telegram] Ошибка подключения: {e}", flush=True)[span_21](start_span)[span_21](end_span)


def parse_fractional_odds(fraction_str):
    """Преобразует дробный коэффициент в десятичный (float)."""
    if not fraction_str or "/" not in fraction_str:
        return None[span_22](start_span)[span_22](end_span)
    try:
        num, denom = fraction_str.split("/")[span_23](start_span)[span_23](end_span)
        decimal_odds = (int(num) / int(denom)) + 1[span_24](start_span)[span_24](end_span)
        return round(decimal_odds, 2)[span_25](start_span)[span_25](end_span)
    except Exception:
        return None[span_26](start_span)[span_26](end_span)


def make_request(url, silent_404=False):
    """Запрос к API Sofascore через cloudscraper с умной ротацией прокси при ошибках."""
    for _ in range(5):  # Максимум 5 попыток со сменой прокси на один запрос
        proxies_dict, addr = get_current_proxies_dict()
        if not proxies_dict:
            rotate_proxy()
            continue
            
        try:
            response = scraper.get(url, proxies=proxies_dict, timeout=10)
            if response.status_code == 200:
                return response.json()[span_27](start_span)[span_27](end_span)
            elif response.status_code == 404 and silent_404:
                return None[span_28](start_span)[span_28](end_span)
            
            print(f"[Ошибка API]: {addr} вернул HTTP {response.status_code}. Меняем прокси...", flush=True)
            rotate_proxy()
        except Exception as e:
            print(f"[Ошибка сети]: {addr} сбоит ({e}). Меняем прокси...", flush=True)
            rotate_proxy()
            
    return None


def get_live_table_tennis_matches():
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live[span_29](start_span)"[span_29](end_span)
    data = make_request(url)
    return data.get("events", []) if data else[span_30](start_span)[span_30](end_span)


def get_match_odds(event_id):
    """Возвращает предматчевые и текущие коэффициенты."""
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/odds/1/all[span_31](start_span)"[span_31](end_span)
    odds_data = make_request(url, silent_404=True)
    
    if odds_data:
        markets = odds_data.get("markets", [])[span_32](start_span)[span_32](end_span)
        for market in markets:
            if market.get("marketName") in ["Match winner", "Full time"]:[span_33](start_span)[span_33](end_span)
                choices = market.get("choices", [])[span_34](start_span)[span_34](end_span)
                if len(choices) >= 2:[span_35](start_span)[span_35](end_span)
                    p1_init_frac = choices[0].get("initialFractionalValue")[span_36](start_span)[span_36](end_span)
                    p2_init_frac = choices[1].get("initialFractionalValue")[span_37](start_span)[span_37](end_span)
                    p1_live_frac = choices[0].get("fractionalValue")[span_38](start_span)[span_38](end_span)
                    p2_live_frac = choices[1].get("fractionalValue")[span_39](start_span)[span_39](end_span)
                    
                    return {
                        "П1_старт": parse_fractional_odds(p1_init_frac),[span_40](start_span)[span_40](end_span)
                        "П2_старт": parse_fractional_odds(p2_init_frac),[span_41](start_span)[span_41](end_span)
                        "П1_лайв": parse_fractional_odds(p1_live_frac),[span_42](start_span)[span_42](end_span)
                        "П2_лайв": parse_fractional_odds(p2_live_frac)[span_43](start_span)[span_43](end_span)
                    }
    return None[span_44](start_span)[span_44](end_span)


def get_player_stats(match_id, side):
    """Анализирует последние 5 матчей игрока."""
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/team-events/{side}[span_45](start_span)"[span_45](end_span)
    data = make_request(url, silent_404=True)
    
    if not data or "events" not in data:[span_46](start_span)[span_46](end_span)
        return {"symbols": "Нет данных", "win_rate": 0.0, "streak": 0}[span_47](start_span)[span_47](end_span)
    
    events = data.get("events", [])[:5][span_48](start_span)[span_48](end_span)
    wins = [][span_49](start_span)[span_49](end_span)
    
    for event in events:
        home_id = event.get("homeTeam", {}).get("id")[span_50](start_span)[span_50](end_span)
        home_score = event.get("homeScore", {}).get("display")[span_51](start_span)[span_51](end_span)
        away_score = event.get("awayScore", {}).get("display")[span_52](start_span)[span_52](end_span)
        
        if home_score is None or away_score is None:[span_53](start_span)[span_53](end_span)
            continue
            
        target_player_id = home_id if side == "home" else event.get("awayTeam", {}).get("id")[span_54](start_span)[span_54](end_span)
        
        if target_player_id == home_id:[span_55](start_span)[span_55](end_span)
            won = home_score > away_score[span_56](start_span)[span_56](end_span)
        else:
            won = away_score > home_score[span_57](start_span)[span_57](end_span)
            
        wins.append(won)[span_58](start_span)[span_58](end_span)
        
    if not wins:[span_59](start_span)[span_59](end_span)
        return {"symbols": "Нет данных", "win_rate": 0.0, "streak": 0}[span_60](start_span)[span_60](end_span)
        
    win_rate = (wins.count(True) / len(wins)) * 100[span_61](start_span)[span_61](end_span)
    
    streak = 0[span_62](start_span)[span_62](end_span)
    for w in wins:[span_63](start_span)[span_63](end_span)
        if w:[span_64](start_span)[span_64](end_span)
            streak += 1[span_65](start_span)[span_65](end_span)
        else:
            break[span_66](start_span)[span_66](end_span)
            
    symbols = "".join(["🟢" if w else "🔴" for w in wins])[span_67](start_span)[span_67](end_span)
    return {"symbols": symbols, "win_rate": round(win_rate, 1), "streak": streak}[span_68](start_span)[span_68](end_span)


def is_tournament_allowed(tournament_name):
    if not tournament_name:[span_69](start_span)[span_69](end_span)
        return False[span_70](start_span)[span_70](end_span)
    name_lower = tournament_name.lower()[span_71](start_span)[span_71](end_span)
    return any(allowed in name_lower for allowed in ALLOWED_TOURNAMENTS)[span_72](start_span)[span_72](end_span)


def monitor_table_tennis():
    global SENT_SIGNALS
    print("=== Двухуровневый фильтр с РОТАЦИЕЙ ПРОКСИ запущен ===", flush=True)
    send_telegram_message(
        f"🤖 <b>Бот успешно перезапущен на Render с пулом прокси!</b>\n"
        f"1️⃣ <b>Камбэк фаворита:</b> винрейт {MIN_WIN_RATE_FAV}%, стрик {MIN_STREAK_FAV}\n"
        f"2️⃣ <b>Равная игра ТОП:</b> винрейт {MIN_WIN_RATE_EQUAL}%, стрик {MIN_STREAK_EQUAL}\n"
        f"🌐 Защита Cloudflare теперь обходится через автоматическую ротацию 10 IP."
    )
    
    while True:
        try:
            matches = get_live_table_tennis_matches()
            if matches:[span_73](start_span)[span_73](end_span)
                current_live_ids = set()[span_74](start_span)[span_74](end_span)
                
                for match in matches:[span_75](start_span)[span_75](end_span)
                    event_id = match.get("id")[span_76](start_span)[span_76](end_span)
                    current_live_ids.add(event_id)[span_77](start_span)[span_77](end_span)
                    
                    if event_id in SENT_SIGNALS:[span_78](start_span)[span_78](end_span)
                        continue
                    
                    tournament_name = match.get("tournament", {}).get("name", "Unknown Tournament")[span_79](start_span)[span_79](end_span)
                    if not is_tournament_allowed(tournament_name):[span_80](start_span)[span_80](end_span)
                        continue
                    
                    odds = get_match_odds(event_id)[span_81](start_span)[span_81](end_span)
                    if not odds or not isinstance(odds, dict):[span_82](start_span)[span_82](end_span)
                        continue
                    
                    p1_start = odds.get("П1_старт")[span_83](start_span)[span_83](end_span)
                    p2_start = odds.get("П2_старт")[span_84](start_span)[span_84](end_span)
                    p1_live = odds.get("П1_лайв")[span_85](start_span)[span_85](end_span)
                    p2_live = odds.get("П2_лайв")[span_86](start_span)[span_86](end_span)
                    
                    if not all([p1_start, p2_start, p1_live, p2_live]):[span_87](start_span)[span_87](end_span)
                        continue
                    
                    home_score = int(match.get("homeScore", {}).get("display", 0))[span_88](start_span)[span_88](end_span)
                    away_score = int(match.get("awayScore", {}).get("display", 0))[span_89](start_span)[span_89](end_span)
                    home_player = match.get("homeTeam", {}).get("name", "Player 1")[span_90](start_span)[span_90](end_span)
                    away_player = match.get("awayTeam", {}).get("name", "Player 2")[span_91](start_span)[span_91](end_span)
                    
                    signal_triggered = False[span_92](start_span)[span_92](end_span)
                    msg_text = "[span_93](start_span)"[span_93](end_span)
                    
                    # --- СЦЕНАРИЙ 1: КАМБЭК ТОП-ФАВОРИТА (Игрок 1) ---
                    if 1.15 <= p1_start <= 1.38 and home_score < away_score and 1.60 <= p1_live <= 2.30:[span_94](start_span)[span_94](end_span)
                        stats = get_player_stats(event_id, "home")[span_95](start_span)[span_95](end_span)
                        if stats["win_rate"] >= MIN_WIN_RATE_FAV and stats["streak"] >= MIN_STREAK_FAV:[span_96](start_span)[span_96](end_span)
                            opp_stats = get_player_stats(event_id, "away")[span_97](start_span)[span_97](end_span)
                            signal_triggered = True[span_98](start_span)[span_98](end_span)
                            msg_text = (
                                f"🔥 <b>СУПЕР-СИГНАЛ: Камбэк ТОП-фаворита!</b>\n\n"
                                f"🏆 {tournament_name}\n[span_99](start_span)"[span_99](end_span)
                                f"⚔️ <b>{home_player}</b> vs {away_player}\n[span_100](start_span)"[span_100](end_span)
                                f"📈 Счет по сетам: <b>{home_score} : {away_score}</b>\n\n[span_101](start_span)"[span_101](end_span)
                                f"📊 <b>Коэффициенты:</b>\n"
                                f"• Старт П1: <code>{p1_start}</code> | <b>Лайв П1: <code>{p1_live}</code></b> 👈\n\n[span_102](start_span)"[span_102](end_span)
                                f"📈 <b>Аналитика фаворита ({home_player}):</b>\n[span_103](start_span)"[span_103](end_span)
                                f"• Последние матчи: {stats['symbols']}\n[span_104](start_span)"[span_104](end_span)
                                f"• Процент побед: <b>{stats['win_rate']}%</b>\n[span_105](start_span)"[span_105](end_span)
                                f"• Серия побед: <b>{stats['streak']}</b>\n\n[span_106](start_span)"[span_106](end_span)
                                f"👤 <b>Соперник ({away_player}):</b> {opp_stats['symbols']}[span_107](start_span)"[span_107](end_span)
                            )
                    
                    # --- СЦЕНАРИЙ 1: КАМБЭК ТОП-ФАВОРИТА (Игрок 2) ---
                    elif 1.15 <= p2_start <= 1.38 and away_score < home_score and 1.60 <= p2_live <= 2.30:[span_108](start_span)[span_108](end_span)
                        stats = get_player_stats(event_id, "away")[span_109](start_span)[span_109](end_span)
                        if stats["win_rate"] >= MIN_WIN_RATE_FAV and stats["streak"] >= MIN_STREAK_FAV:[span_110](start_span)[span_110](end_span)
                            opp_stats = get_player_stats(event_id, "home")[span_111](start_span)[span_111](end_span)
                            signal_triggered = True[span_112](start_span)[span_112](end_span)
                            msg_text = (
                                f"🔥 <b>СУПЕР-СИГНАЛ: Камбэк ТОП-фаворита!</b>\n\n"
                                f"🏆 {tournament_name}\n[span_113](start_span)"[span_113](end_span)
                                f"⚔️ {home_player} vs <b>{away_player}</b>\n[span_114](start_span)"[span_114](end_span)
                                f"📈 Счет по сетам: <b>{home_score} : {away_score}</b>\n\n[span_115](start_span)"[span_115](end_span)
                                f"📊 <b>Коэффициенты:</b>\n"
                                f"• Старт П2: <code>{p2_start}</code> | <b>Лайв П2: <code>{p2_live}</code></b> 👈\n\n[span_116](start_span)"[span_116](end_span)
                                f"📈 <b>Аналитика фаворита ({away_player}):</b>\n[span_117](start_span)"[span_117](end_span)
                                f"• Последние матчи: {stats['symbols']}\n[span_118](start_span)"[span_118](end_span)
                                f"• Процент побед: <b>{stats['win_rate']}%</b>\n[span_119](start_span)"[span_119](end_span)
                                f"• Серия побед: <b>{stats['streak']}</b>\n\n[span_120](start_span)"[span_120](end_span)
                                f"👤 <b>Соперник ({home_player}):</b> {opp_stats['symbols']}[span_121](start_span)"[span_121](end_span)
                            )
                    
                    # --- СЦЕНАРИЙ 2: РАВНАЯ ИГРА ТОПОВ (Счет 1:1 по сетам) ---
                    if not signal_triggered and (home_score == 1 and away_score == 1):[span_122](start_span)[span_122](end_span)
                        if 1.85 <= p1_live <= 2.20:[span_123](start_span)[span_123](end_span)
                            p1_stats = get_player_stats(event_id, "home")[span_124](start_span)[span_124](end_span)
                            if p1_stats["win_rate"] >= MIN_WIN_RATE_EQUAL and p1_stats["streak"] >= MIN_STREAK_EQUAL:[span_125](start_span)[span_125](end_span)
                                p2_stats = get_player_stats(event_id, "away")[span_126](start_span)[span_126](end_span)
                                signal_triggered = True[span_127](start_span)[span_127](end_span)
                                msg_text = (
                                    f"⚡ <b>СИГНАЛ: Равная игра ТОП-игроков!</b>\n\n"
                                    f"🏆 {tournament_name}\n[span_128](start_span)"[span_128](end_span)
                                    f"⚔️ <b>{home_player}</b> vs {away_player}\n[span_129](start_span)"[span_129](end_span)
                                    f"📈 Счет по сетам: <b>1 : 1</b>\n\n[span_130](start_span)"[span_130](end_span)
                                    f"📊 <b>Коэффициенты:</b>\n"
                                    f"• <b>Лайв П1: <code>{p1_live}</code></b> 👈\n\n[span_131](start_span)"[span_131](end_span)
                                    f"📈 <b>Аналитика ({home_player}):</b>\n[span_132](start_span)"[span_132](end_span)
                                    f"• Форма: {p1_stats['symbols']} (Винрейт: {p1_stats['win_rate']}%, Стрик: {p1_stats['streak']})\n\n[span_133](start_span)"[span_133](end_span)
                                    f"👤 <b>Соперник ({away_player}):</b>\n[span_134](start_span)"[span_134](end_span)
                                    f"• Форма: {p2_stats['symbols']} (Винрейт: {p2_stats['win_rate']}%)[span_135](start_span)"[span_135](end_span)
                                )
                        
                        elif 1.85 <= p2_live <= 2.20:[span_136](start_span)[span_136](end_span)
                            p2_stats = get_player_stats(event_id, "away")[span_137](start_span)[span_137](end_span)
                            if p2_stats["win_rate"] >= MIN_WIN_RATE_EQUAL and p2_stats["streak"] >= MIN_STREAK_EQUAL:[span_138](start_span)[span_138](end_span)
                                p1_stats = get_player_stats(event_id, "home")[span_139](start_span)[span_139](end_span)
                                signal_triggered = True[span_140](start_span)[span_140](end_span)
                                msg_text = (
                                    f"⚡ <b>СИГНАЛ: Равная игра ТОП-игроков!</b>\n\n"
                                    f"🏆 {tournament_name}\n[span_141](start_span)"[span_141](end_span)
                                    f"⚔️ {home_player} vs <b>{away_player}</b>\n[span_142](start_span)"[span_142](end_span)
                                    f"📈 Счет по сетам: <b>1 : 1</b>\n\n[span_143](start_span)"[span_143](end_span)
                                    f"📊 <b>Коэффициенты:</b>\n"
                                    f"• <b>Лайв П2: <code>{p2_live}</code></b> 👈\n\n[span_144](start_span)"[span_144](end_span)
                                    f"📈 <b>Аналитика ({away_player}):</b>\n[span_145](start_span)"[span_145](end_span)
                                    f"• Форма: {p2_stats['symbols']} (Винрейт: {p2_stats['win_rate']}%, Стрик: {p2_stats['streak']})\n\n[span_146](start_span)"[span_146](end_span)
                                    f"👤 <b>Соперник ({home_player}):</b>\n[span_147](start_span)"[span_147](end_span)
                                    f"• Форма: {p1_stats['symbols']} (Винрейт: {p1_stats['win_rate']}%)[span_148](start_span)"[span_148](end_span)
                                )
                    
                    if signal_triggered:[span_149](start_span)[span_149](end_span)
                        print(f"[ОТПРАВЛЕНО] {home_player} - {away_player} ({tournament_name})", flush=True)[span_150](start_span)[span_150](end_span)
                        send_telegram_message(msg_text)[span_151](start_span)[span_151](end_span)
                        SENT_SIGNALS.add(event_id)[span_152](start_span)[span_152](end_span)
                    
                    time.sleep(1.2)[span_153](start_span)[span_153](end_span)
                
                expired_matches = SENT_SIGNALS - current_live_ids[span_154](start_span)[span_154](end_span)
                if expired_matches:[span_155](start_span)[span_155](end_span)
                    SENT_SIGNALS -= expired_matches[span_156](start_span)[span_156](end_span)
            else:
                print("Сейчас нет активных лайв-матчей.", flush=True)[span_157](start_span)[span_157](end_span)
                
        except Exception as e:
            print(f"[Фоновая ошибка мониторинга]: {e}", flush=True)[span_158](start_span)[span_158](end_span)
            
        print("Сканирование завершено. Ожидание 30 сек...", flush=True)[span_159](start_span)[span_159](end_span)
        time.sleep(30)[span_160](start_span)[span_160](end_span)


# --- МИКРО-ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)[span_161](start_span)[span_161](end_span)

@app.route('/')
def home():
    return "Ротационный бот работает 24/7!"

print("[SYSTEM] Старт фонового потока мониторинга Sofascore...", flush=True)[span_162](start_span)[span_162](end_span)
threading.Thread(target=monitor_table_tennis, daemon=True).start()[span_163](start_span)[span_163](end_span)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))[span_164](start_span)[span_164](end_span)
    app.run(host="0.0.0.0", port=port)[span_165](start_span)[span_165](end_span)
