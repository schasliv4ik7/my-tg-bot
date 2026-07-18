def make_request(url):
    # Временно тестируем БЕЗ прокси, так как текущий выдает 502 Bad Gateway
    for attempt in range(3):
        try:
            # Делаем запрос напрямую через cloudscraper
            response = scraper.get(url, timeout=12)
            if response.status_code == 200:
                return response.json()
            print(f"[STS API Ошибка]: Код {response.status_code}, попытка {attempt + 1}", flush=True)
        except Exception as e:
            print(f"[STS Сеть Ошибка]: {e}, попытка {attempt + 1}", flush=True)
        time.sleep(3)
    return None
