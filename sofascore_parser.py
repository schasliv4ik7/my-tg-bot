import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

def monitor():
    print("--- [СИСТЕМА] Мониторинг запущен (с усиленной маскировкой) ---", flush=True)
    # Расширенный набор заголовков для обхода 403 ошибки
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "Connection": "keep-alive"
    }
    
    while True:
        try:
            response = requests.get(
                "https://api.sofascore.com/api/v1/sport/table-tennis/events/live", 
                headers=headers, 
                timeout=15
            )
            print(f"--- Статус: {response.status_code} ---", flush=True)
            
            if response.status_code == 200:
                print("--- [УСПЕХ] Данные успешно получены! ---", flush=True)
                # Здесь можно добавить логику парсинга JSON
            else:
                print(f"--- [ПРЕДУПРЕЖДЕНИЕ] Код ответа: {response.status_code} ---", flush=True)
                
        except Exception as e:
            print(f"--- Ошибка: {e} ---", flush=True)
        time.sleep(60)

threading.Thread(target=monitor, daemon=True).start()

@app.route('/')
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
