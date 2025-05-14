import os
import json
import logging
from datetime import time, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Application,
)
from pytz import timezone
from dotenv import load_dotenv

# Параметры
DATA_FILE = "data.json"
TIMEZONE = timezone("Asia/Ho_Chi_Minh")

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables")

# Логирование
logging.basicConfig(level=logging.INFO)

# Задачи
TASKS = {
    "garden_morning": {"name": "Полить цветы в саду (утро)", "hour": 9, "minute": 0},
    "garden_evening": {"name": "Полить цветы в саду (вечер)", "hour": 20, "minute": 0},
    "spray_plants": {"name": "Растения хотят водички - спрей цветов! :)", "hour": 13, "minute": 0},
    "dishwasher_unload": {"name": "Разгрузи посудомойку", "hour": 10, "minute": 0},
    "dishwasher_load": {"name": "Загрузи посудомойку", "hour": 20, "minute": 0},
}

# Загрузка/сохранение данных
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"chats": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Клавиатура задач
def get_keyboard(task_key: str) -> InlineKeyboardMarkup:
    if task_key in ["garden_morning", "garden_evening"]:
        buttons = [
            [InlineKeyboardButton("🌧 Быф дождяф", callback_data=f"done_rain|{task_key}")],
            [InlineKeyboardButton("✅ Я полив :)", callback_data=f"done_user|{task_key}")],
            [InlineKeyboardButton("😢 Отстань на 30 минут", callback_data=f"remind_30|{task_key}")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton("✅ Я сделяль :)", callback_data=f"done_user|{task_key}")],
            [InlineKeyboardButton("😢 Отстань на 30 минут", callback_data=f"remind_30|{task_key}")],
        ]
    return InlineKeyboardMarkup(buttons)

# Планирование задач
async def schedule_jobs(application: Application, chat_id: int):
    for task_key, task in TASKS.items():
        application.job_queue.run_daily(
            send_reminder,
            time=time(task["hour"], task["minute"], tzinfo=TIMEZONE),
            days=(0, 1, 2, 3, 4, 5, 6),
            data={"chat_id": chat_id, "task_key": task_key}
        )

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    chat_id = update.effective_chat.id
    if str(chat_id) not in data["chats"]:
        data["chats"][str(chat_id)] = {"active": True}
        save_data(data)
    await update.message.reply_text("Привет! Я бот-напоминалка 😊 Буду каждый день напоминать о важных делах.")
    await schedule_jobs(context.application, chat_id)

# Команда /list
async def task_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(task["name"], callback_data=f"view|{key}")]
        for key, task in TASKS.items()
    ]
    text = "\n".join([f"📌 {task['name']}" for task in TASKS.values()])
    await update.message.reply_text(f"Список задач:\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))

# Отправка напоминания
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    task_key = job_data['task_key']
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 Напоминание: {TASKS[task_key]['name']}",
        reply_markup=get_keyboard(task_key)
    )

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, task_key = query.data.split('|')

    if action == "view":
        await query.message.reply_text(
            f"🔔 Напоминание: {TASKS[task_key]['name']}",
            reply_markup=get_keyboard(task_key)
        )
    elif action == "done_rain":
        await query.edit_message_text("🌧 Дождь полив :)")
    elif action == "done_user":
        await query.edit_message_text("✅ Пасиба))))")
    elif action == "remind_30":
        await query.edit_message_text("🔁 Напомню через 30 минут")
        context.job_queue.run_once(
            send_reminder,
            when=timedelta(minutes=30),
            data={"chat_id": query.message.chat.id, "task_key": task_key}
        )

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", task_list))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
