import os
import logging
import sqlite3
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    Application,
)
from pytz import timezone
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# Настройка часового пояса
TIMEZONE = timezone("Asia/Ho_Chi_Minh")

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# Файл базы данных
DB_FILE = "reminders.db"

# Список ежедневных задач
TASKS = {
    "garden_morning": {"name": "Полить цветы в саду (утро)", "hour": 9, "minute": 0, "days": (0, 1, 2, 3, 4, 5, 6)},
    "garden_evening": {"name": "Полить цветы в саду (вечер)", "hour": 20, "minute": 0, "days": (0, 1, 2, 3, 4, 5, 6)},
    "spray_plants": {"name": "Растения хотят водички - спрей цветов! :)", "hour": 13, "minute": 0, "days": (1, 3, 5)},
    "dishwasher_unload": {"name": "Разгрузи посудомойку", "hour": 10, "minute": 0, "days": (0, 1, 2, 3, 4)},
    "dishwasher_load": {"name": "Загрузи посудомойку", "hour": 20, "minute": 0, "days": (0, 1, 2, 3, 4)},
}

user_pending_tasks = {}

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот-напоминалка 😊 Используй /add_notify чтобы добавить задачу.")

async def task_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здесь будет список всех задач (в разработке)")

async def list_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здесь будет список задач на сегодня (в разработке)")

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("DEBUG: пока ничего не показываю")

async def add_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("Введите название задачи:")
    context.user_data['awaiting_task_name'] = True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.user_data.get("awaiting_task_name"):
        task_name = update.message.text.strip()
        user_pending_tasks[chat_id] = {"task_name": task_name}
        context.user_data["awaiting_task_name"] = False

        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        keyboard = [[InlineKeyboardButton(day, callback_data=f"day|{i}")] for i, day in enumerate(days)]
        keyboard.append([InlineKeyboardButton("Ввести дату", callback_data="custom_date")])
        await update.message.reply_text("Выберите день недели или введите дату:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif context.user_data.get("awaiting_date"):
        try:
            date_parts = list(map(int, update.message.text.strip().split()))
            if len(date_parts) != 3:
                raise ValueError
            reminder_date = datetime(date_parts[2], date_parts[1], date_parts[0], tzinfo=TIMEZONE)
            now = datetime.now(TIMEZONE)
            if reminder_date.date() < now.date():
                await update.message.reply_text("Дата не может быть в прошлом. Пожалуйста, введите корректную дату.")
                return
            task_info = user_pending_tasks.get(chat_id)
            if task_info:
                context.user_data["reminder_date"] = reminder_date
                context.user_data["awaiting_date"] = False
                await ask_time(update, context)
        except ValueError:
            await update.message.reply_text("Формат: ДД ММ ГГГГ")

    elif context.user_data.get("awaiting_time"):
        try:
            time_parts = list(map(int, update.message.text.strip().split(":")))
            if len(time_parts) != 2:
                raise ValueError
            reminder_time = time(time_parts[0], time_parts[1])
            reminder_date = context.user_data.get("reminder_date")
            if reminder_date:
                reminder_datetime = datetime.combine(reminder_date.date(), reminder_time, tzinfo=TIMEZONE)
                task_info = user_pending_tasks.get(chat_id)
                if task_info:
                    save_user_task(chat_id, task_info["task_name"], reminder_datetime)
                    await update.message.reply_text("Задача добавлена!")
                    user_pending_tasks.pop(chat_id, None)
                    context.user_data["awaiting_time"] = False
        except ValueError:
            await update.message.reply_text("Формат времени: ЧЧ:ММ")

async def ask_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    times = [f"{hour:02d}:00" for hour in range(6, 22)]
    keyboard = [[InlineKeyboardButton(t, callback_data=f"time|{t}")] for t in times]
    await update.message.reply_text("Выберите время напоминания:", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["awaiting_time"] = True

async def notify_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    if data.startswith("day"):
        _, day_index = data.split("|")
        day_index = int(day_index)
        now = datetime.now(TIMEZONE)
        days_ahead = (day_index - now.weekday()) % 7
        reminder_date = now + timedelta(days=days_ahead)
        task_info = user_pending_tasks.get(chat_id)
        if task_info:
            context.user_data["reminder_date"] = reminder_date
            await ask_time(update, context)

    elif data == "custom_date":
        await query.edit_message_text("Введите дату в формате: ДД ММ ГГГГ")
        context.user_data["awaiting_date"] = True

    elif data.startswith("time"):
        _, time_str = data.split("|")
        reminder_time = datetime.strptime(time_str, "%H:%M").time()
        reminder_date = context.user_data.get("reminder_date")
        if reminder_date:
            reminder_datetime = datetime.combine(reminder_date.date(), reminder_time, tzinfo=TIMEZONE)
            task_info = user_pending_tasks.get(chat_id)
            if task_info:
                save_user_task(chat_id, task_info["task_name"], reminder_datetime)
                await query.edit_message_text("Задача добавлена!")
                user_pending_tasks.pop(chat_id, None)
                context.user_data["awaiting_time"] = False

def save_user_task(chat_id: int, task_name: str, reminder_datetime: datetime):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO reminders (chat_id, task_key, task_name, remind_time, remind_date, task_type)
            VALUES (?, ?, ?, ?, ?, 'user')
        ''', (chat_id, task_name, task_name, reminder_datetime.strftime("%H:%M"), reminder_datetime.strftime("%Y-%m-%d")))
        conn.commit()

def add_daily_tasks():
    today = datetime.now(TIMEZONE).date()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        for key, task in TASKS.items():
            if today.weekday() in task["days"]:
                c.execute('''
                    SELECT 1 FROM reminders WHERE task_key = ? AND remind_date = ? AND task_type = 'daily'
                ''', (key, today.strftime("%Y-%m-%d")))
                if not c.fetchone():
                    remind_time = time(task["hour"], task["minute"])
                    c.execute('''
                        INSERT INTO reminders (chat_id, task_key, task_name, remind_time, remind_date, task_type)
                        VALUES (?, ?, ?, ?, ?, 'daily')
                    ''', (0, key, task["name"], remind_time.strftime("%H:%M"), today.strftime("%Y-%m-%d")))
        conn.commit()

async def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(add_daily_tasks, 'cron', hour=0, minute=1)
    scheduler.start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", task_list))
    app.add_handler(CommandHandler("list_daily", list_daily))
    app.add_handler(CommandHandler("add_notify", add_notify))
    app.add_handler(CommandHandler("debug", debug))

    app.add_handler(CallbackQueryHandler(notify_button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
