import os
import time
import threading
import httpx
from flask import Flask

app = Flask(__name__)

def monitor():
    print("--- [СИСТЕМА] Мониторинг запущен (ПРЯМОЙ ДОСТУП) ---", flush=True)
    while True:
        try:
            # Запрос без прокси
            resp = httpx.get("https://api.sofascore.com/api/v1/sport/table-tennis/events/live", timeout=15.0)
            print(f"--- [СЕТЬ] Статус ответа: {resp.status_code} ---", flush=True)
            if resp.status_code == 200:
                print("--- [УСПЕХ] Данные получены! ---", flush=True)
            else:
                print(f"--- [ПРЕДУПРЕЖДЕНИЕ] Код ответа: {resp.status_code} ---", flush=True)
        except Exception as e:
            print(f"--- [ОШИБКА] {str(e)} ---", flush=True)
        time.sleep(60)

threading.Thread(target=monitor, daemon=True).start()

@app.route('/')
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
