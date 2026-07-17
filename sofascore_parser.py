import json
import urllib.request
import urllib.parse
import time
import ssl
import threading
import os
import cloudscraper  # <-- НОВАЯ БИБЛИОТЕКА ДЛЯ ОБХОДА 403 / CLOUDFLARE
from flask import Flask

# --- НАСТРОЙКИ TELEGRAM ---
BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

# Отключение проверки SSL для Telegram-запросов
SSL_CONTEXT = ssl._create_unverified_context()

# Множество для отправленных сигналов
SENT_SIGNALS = set()

# Создаем умный сканер, который умеет обходить защиту Cloudflare
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)


def send_telegram_message(text):
    """Отправляет форматированное сообщение в Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": YOUR_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
            if response.status != 200:
                print(f"[Telegram] Ошибка отправки: {response.status}", flush=True)
    except Exception as e:
        print(f"[Telegram] Ошибка подключения: {e}", flush=True)


def make_request(url, silent_404=False):
    """Запрос к API Sofascore через cloudscraper для обхода Cloudflare 403."""
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404 and silent_404:
            return None
        
        print(f"[Ошибка запроса]: HTTP Status {response.status_code}", flush=True)
        return None
    except Exception as e:
        print(f"[Ошибка сетевого запроса]: {e}", flush=True)
        return None


def get_live_table_tennis_matches():
    url = "https://api.sofascore.com/api/v1/sport/table-tennis/events/live"
    data = make_request(url)
    return data.get("events", []) if data else []


def monitor_table_tennis():
    global SENT_SIGNALS
    print("=== ТЕСТОВЫЙ РЕЖИМ: ФИЛЬТРЫ ОТКЛЮЧЕНЫ ===", flush=True)
    send_telegram_message("⚠️ <b>Бот запущен на ноутбуке в РЕЖИМЕ ТЕСТА! Фильтры отключены. Ждем первый матч...</b>")
    
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
                    home_score = int(match.get("homeScore", {}).get("display", 0))
                    away_score = int(match.get("awayScore", {}).get("display", 0))
                    home_player = match.get("homeTeam", {}).get("name", "Player 1")
                    away_player = match.get("awayTeam", {}).get("name", "Player 2")
                    
                    # Имитируем успешное срабатывание сигнала для ЛЮБОГО матча
                    msg_text = (
                        f"✅ <b>ТЕСТОВЫЙ СИГНАЛ ПРОШЕЛ УСПЕШНО!</b>\n\n"
                        f"🏆 Лига: {tournament_name}\n"
                        f"⚔️ Матч: <b>{home_player}</b> vs {away_player}\n"
                        f"📈 Счет по сетам: <b>{home_score} : {away_score}</b>\n\n"
                        f"🚀 Если ты видишь это сообщение, значит парсинг на ноутбуке работает, а токен Telegram и Chat ID указаны верно!"
                    )
                    
                    print(f"[ТЕСТ ОТПРАВКИ] Найдена игра: {home_player} - {away_player}", flush=True)
                    send_telegram_message(msg_text)
                    SENT_SIGNALS.add(event_id)
                    break # Отправляем только ОДИН первый попавшийся матч и завершаем цикл сканирования
                    
                # Безопасное удаление завершенных матчей
                expired_matches = SENT_SIGNALS - current_live_ids
                if expired_matches:
                    SENT_SIGNALS -= expired_matches
            else:
                print("Сейчас нет активных лайв-матчей.", flush=True)
                
        except Exception as e:
            print(f"[Фоновая ошибка мониторинга]: {e}", flush=True)
            
        print("Тестовое сканирование завершено. Ожидание 30 сек...", flush=True)
        time.sleep(30)


# --- МИКРО-ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Тестовый бот активен!"


print("[SYSTEM] Старт фонового потока мониторинга Sofascore...", flush=True)
threading.Thread(target=monitor_table_tennis, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
