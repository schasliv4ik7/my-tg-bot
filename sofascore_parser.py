import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

def monitor():
    print("--- [СИСТЕМА] Мониторинг запущен (requests) ---", flush=True)
    while True:
        try:
            # Прямой запрос без прокси для максимальной стабильности
            response = requests.get("https://api.sofascore.com/api/v1/sport/table-tennis/events/live", timeout=10)
            print(f"--- Статус: {response.status_code} ---", flush=True)
        except Exception as e:
            print(f"--- Ошибка: {e} ---", flush=True)
        time.sleep(60)

threading.Thread(target=monitor, daemon=True).start()

@app.route('/')
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
