def monitor_sts_table_tennis():
    print("=== Мониторинг линии STS.pl запущен (БЕЗ ПРОКСИ) ===", flush=True)
    send_telegram_message("🤖 <b>Бот успешно перезапущен на STS.pl!</b>\nПроверяем официальный API эндпоинт.")
    
    # Использование официального базового домена для обхода NameResolutionError
    url = "https://www.sts.pl/api/v1/sports/live/211" 
    
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
                        
                    scores = event.get("score", {})
                    home_score = int(scores.get("home", 0))
                    away_score = int(scores.get("away", 0))
                    
                    home_player = event.get("homeTeam", {}).get("name", "Игрок 1")
                    away_player = event.get("awayTeam", {}).get("name", "Игрок 2")
                    tournament = event.get("category", {}).get("name", "Турнир STS")
                    
                    markets = event.get("markets", [])
                    p1_live, p2_live = None, None
                    
                    for m in markets:
                        if m.get("type") in ["match_winner", "12"]:
                            outcomes = m.get("outcomes", [])
                            if len(outcomes) >= 2:
                                p1_live = float(outcomes[0].get("price", 0))
                                p2_live = float(outcomes[1].get("price", 0))
                                break
                    
                    if not p1_live or not p2_live:
                        continue
                        
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
                
                expired = SENT_SIGNALS - current_live_ids
                if expired:
                    SENT_SIGNALS.difference_update(expired)
            else:
                print("На STS сейчас нет активных live-матчей или API вернул пустой ответ.", flush=True)
                
        except Exception as e:
            print(f"[Ошибка цикла мониторинга STS]: {e}", flush=True)
            
        time.sleep(30)
