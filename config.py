"""
config.py — глобальная конфигурация проекта

Хранит:
- Путь к БД
- Часовой пояс
- Токен бота
"""

import os
from dotenv import load_dotenv
from pytz import timezone

# Путь к SQLite базе
DB_FILE = "reminders.db"

# Часовой пояс
TIMEZONE = timezone("Asia/Ho_Chi_Minh")

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables")
