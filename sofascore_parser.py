import os
import time
import random
import threading
import httpx
from flask import Flask, Response

# --- НАСТРОЙКИ TELEGRAM ---
BOT_TOKEN = "8225494453:AAG55D-7g0jxrQAyRsWK1qyJkK3mf0WGMgM"
YOUR_CHAT_ID = "5777477925"

# --- ТВОЙ РАБОЧИЙ HTTP ПРОКСИ ---
PROXY_URL = "http://aeeufstt:mmzjzap1e8nc@84.247.60.125:6095"
USE_PROXY = True

# Список популярных мобильных User-Agent
MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
]

SENT_SIGNALS = set()
TARGET_LEAGUES = ["setka cup", "liga pro", "tt cup", "win cup", "challenger series"]

# Настраиваем клиент HTTPX на работу через HTTP-прокси
if USE_PROXY:
    limits = httpx.Limits(max_keepalive_connections=0, max_connections=5)
    client = httpx.Client(
        proxy=PROXY_URL,
        verify=False,
        limits=limits,
        timeout=20.0
    )
else:
    client = httpx.Client(
        verify=False,
        timeout=15.0
    )


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
