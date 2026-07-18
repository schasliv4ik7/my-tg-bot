import json
import urllib.request
import urllib.parse
import time
import ssl
import threading
import os
import cloudscraper
from flask import Flask

# --- НАСТРОЙКИ TELEGRAM ---
BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

# --- ТВОЙ РАБОЧИЙ ПРОКСИ ---
PROXY_RAW = "158.46.145.135:64310:TvSYGxHL:H19ycY2V"

# Отключение проверки SSL для Telegram
SSL_CONTEXT = ssl._create_unverified_context()
SENT_SIGNALS = set()

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

# Заголовки под польский сегмент STS
scraper.headers.update({
    "accept": "application/json, text/plain, */*",
    "accept-language": "pl-PL,pl;q=0.9,en;q=0.8",
    "origin": "https://www.sts.pl",
    "referer": "https://www.sts.pl/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
})

def get_proxy_dict():
    try:
        ip, port, user, password = PROXY_RAW.split(":")
        proxy_address = f"{user}:{password}@{ip}:{port}"
        return {
            "http": f"http://{proxy_address}",
            "https": f"http://{proxy_address}"
        }
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА ПРОКСИ]: {e}", flush=True)
        return None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as response:
            if response.status != 200:
                print(f"[Telegram] Ошибка: {response.status}", flush=True)
    except Exception as e:
        print(f"[Telegram] Исключение: {e}", flush=True)

def make_request(url):
    proxies_dict = get_proxy_dict()
    if not proxies_dict:
        return None
    for attempt in range(3):
        try:
            response = scraper.get(url, proxies=proxies_dict, timeout=12)
            if response.status_code == 200:
                return response.json()
            print(f"[STS API Ошибка]: Код {response.status_code}, попытка {attempt + 1}", flush=True)
        except Exception as e:
            print(f"[STS Сеть Ошибка]: {e}, попытка {attempt + 1}", flush=True)
        time.sleep(3)
    return None

def monitor_sts_table_tennis():
    print("=== Мониторинг линии STS.pl запущен ===", flush=True)
    send_telegram_message("🤖 <b>Бот успешно переключен на линию STS.pl!</b>\nПроверяем лайв настольного тенниса.")
    
    # URL структуры live-линии STS (раздел настольного тенниса)
    # 211 — стандартный ID настольного тенниса в сетке большинства европейских платформ, включая STS
    url = "https://awb-api.sts.pl/api/v1/sports/live/211" 
    
    while True:
        try:
            data = make_request(url)
            if data and "events" in data:
                events = data["events"]
                current_live_ids = set()
                
                for event in events:
                    event_id = event.get("id")
                    current_live_ids.add(event_id)
                    
                    if event_id in SENT_SIGNALS:
                        continue
                        
                    # Извлекаем счет по сетам
                    # У STS счет обычно лежит в объекте liveStatus или текущих результатах парсинга
                    scores = event.get("score", {})
                    home_score = int(scores.get("home", 0))
                    away_score = int(scores.get("away", 0))
                    
                    home_player = event.get("homeTeam", {}).get("name", "Игрок 1")
                    away_player = event.get("awayTeam", {}).get("name", "Игрок 2")
                    tournament = event.get("category", {}).get("name", "Турнир STS")
                    
                    # Извлекаем коэффициенты на исход (П1 / П2)
                    markets = event.get("markets", [])
                    p1_live, p2_live = None, None
                    
                    for m in markets:
                        if m.get("type") in ["match_winner", "12"]: # Основной исход матча
                            outcomes = m.get("outcomes", [])
                            if len(outcomes) >= 2:
                                p1_live = float(outcomes[0].get("price", 0))
                                p2_live = float(outcomes[1].get("price", 0))
                                break
                    
                    if not p1_live or not p2_live:
                        continue
                        
                    # Сценарий: Равная игра топов (Счет 1:1 по сетам)
                    if home_score == 1 and away_score == 1:
                        msg = (
                            f"⚡ <b>STS.pl: Равная игра (1:1 по сетам)!</b>\n\n"
                            f"🏆 {tournament}\n"
                            f"⚔️ <b>{home_player}</b> vs <b>{away_player}</b>\n"
                            f"📈 Текущий счет: <b>1 : 1</b>\n\n"
                            f"📊 <b>Коэффициенты STS:</b>\n"
                            f"• П1: <code>{p1_live}</code>\n"
                            f"• П2: <code>{p2_live}</code>"
                        )
                        send_telegram_message(msg)
                        SENT_SIGNALS.add(event_id)
                        print(f"[СИГНАЛ ОТПРАВЛЕН] {home_player} - {away_player}", flush=True)
                
                # Чистим старые завершенные матчи
                expired = SENT_SIGNALS - current_live_ids
                if expired:
                    SENT_SIGNALS.difference_update(expired)
            else:
                print("На STS сейчас нет активных live-матчей в выбранной категории или API ответил пустотой.", flush=True)
                
        except Exception as e:
            print(f"[Ошибка цикла мониторинга STS]: {e}", flush=True)
            
        time.sleep(30)

# --- ВЕБ-СЕРВЕР ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Парсер линии STS активен."

threading.Thread(target=monitor_sts_table_tennis, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
