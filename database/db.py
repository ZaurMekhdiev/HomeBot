"""
database/db.py — логика работы с базой данных SQLite для хранения напоминаний

Функции:
- init_db: инициализация таблицы
- save_user_task: сохранение пользовательской задачи
- add_daily_tasks: добавление системных задач по расписанию
"""

import sqlite3
import uuid
from datetime import datetime, time
from config import DB_FILE, TIMEZONE
from logic.tasks import TASKS

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                task_key TEXT NOT NULL,
                task_name TEXT NOT NULL,
                remind_time TEXT NOT NULL,
                remind_date TEXT NOT NULL,
                snooze_minutes INTEGER DEFAULT 0,
                next_reminder TEXT,
                is_completed INTEGER DEFAULT 0,
                completed_by TEXT,
                completed_at TEXT,
                task_type TEXT DEFAULT 'user'
            )
        ''')
        conn.commit()

def save_user_task(chat_id: int, task_name: str, reminder_datetime: datetime):
    task_key = f"user_{uuid.uuid4().hex[:8]}"
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO reminders (chat_id, task_key, task_name, remind_time, remind_date, task_type)
            VALUES (?, ?, ?, ?, ?, 'user')
        ''', (
            chat_id,
            task_key,
            task_name,
            reminder_datetime.strftime("%H:%M"),
            reminder_datetime.strftime("%Y-%m-%d")
        ))
        conn.commit()

def add_daily_tasks():
    today = datetime.now(TIMEZONE).date()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        # 1. Удаление устаревших задач старше 7 дней
        c.execute('''
            DELETE FROM reminders
            WHERE task_type = 'daily' AND DATE(remind_date) < DATE(?,'-7 day')
        ''', (today.strftime("%Y-%m-%d"),))

        # 2. Обнуление статуса выполненных задач на сегодня
        c.execute('''
            UPDATE reminders
            SET is_completed = 0, completed_by = NULL, completed_at = NULL
            WHERE task_type = 'daily' AND remind_date = ?
        ''', (today.strftime("%Y-%m-%d"),))

        # 3. Добавление задач, если они отсутствуют
        for key, task in TASKS.items():
            if today.weekday() in task["days"]:
                c.execute('''
                    SELECT 1 FROM reminders
                    WHERE task_key = ? AND remind_date = ? AND task_type = 'daily'
                ''', (key, today.strftime("%Y-%m-%d")))
                if not c.fetchone():
                    remind_time = time(task["hour"], task["minute"])
                    c.execute('''
                        INSERT INTO reminders (chat_id, task_key, task_name, remind_time, remind_date, task_type)
                        VALUES (?, ?, ?, ?, ?, 'daily')
                    ''', (0, key, task["name"], remind_time.strftime("%H:%M"), today.strftime("%Y-%m-%d")))
        conn.commit()

