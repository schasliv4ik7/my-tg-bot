def monitor():
    print("--- [СИСТЕМА] Поток мониторинга запущен (ВЕРСИЯ БЕЗ КЛИЕНТА) ---", flush=True)
    while True:
        proxy_url = random.choice(PROXIES)
        print(f"--- [СЕТЬ] Попытка через: {proxy_url.split('@')[1]} ---", flush=True)
        
        try:
            # Используем прямой вызов httpx.get, это гарантированно не вызовет ошибку Client.__init__
            resp = httpx.get(
                "https://api.sofascore.com/api/v1/sport/table-tennis/events/live",
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0,
                verify=False
            )
            
            print(f"--- [СЕТЬ] Статус ответа: {resp.status_code} ---", flush=True)
            if resp.status_code == 200:
                print("--- [УСПЕХ] Данные получены! ---", flush=True)
            else:
                print(f"--- [ОШИБКА] Сервер вернул код: {resp.status_code} ---", flush=True)
        except Exception as e:
            # Выводим тип ошибки, чтобы понять, если проблема останется
            print(f"--- [КРИТИЧЕСКАЯ ОШИБКА] {type(e).__name__}: {str(e)} ---", flush=True)
            
        time.sleep(60)
