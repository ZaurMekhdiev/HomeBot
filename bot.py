import os
import logging
from datetime import time, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
    Application
)
from pytz import timezone
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Устанавливаем таймзону Вьетнама
local_tz = timezone("Asia/Ho_Chi_Minh")

# Хранилище задач
TASKS = {
    "garden_morning": {"name": "Полить цветы в саду (утро)", "hour": 9, "minute": 0},
    "garden_evening": {"name": "Полить цветы в саду (вечер)", "hour": 20, "minute": 0},
    "spray_plants": {"name": "Растения хотят водички - спрей цветов! :)", "hour": 13, "minute": 0},
    "dishwasher_unload": {"name": "Разгрузи посудомойку", "hour": 10, "minute": 0},
    "dishwasher_load": {"name": "Загрузи посудомойку", "hour": 20, "minute": 0},
}

# Глобальный chat_id группы
group_chat_id = None

# Универсальная клавиатура

def get_keyboard(task_key: str) -> InlineKeyboardMarkup:
    if task_key in ["garden_morning", "garden_evening"]:
        buttons = [
            [InlineKeyboardButton("\U0001F327 Быф дождяф\U0001F327", callback_data=f"done_rain|{task_key}")],
            [InlineKeyboardButton("\u2705 Я полив :)", callback_data=f"done_user|{task_key}")],
            [InlineKeyboardButton("\U0001F62D Отстань на 30 минут плз", callback_data=f"remind_30|{task_key}")],
        ]
    elif task_key == "spray_plants":
        buttons = [
            [InlineKeyboardButton("\u2705 Я сделяль :)", callback_data=f"done_user|{task_key}")],
            [InlineKeyboardButton("\U0001F62D Отстань на 30 минут плз", callback_data=f"remind_30|{task_key}")],
        ]
    elif task_key in ["dishwasher_unload", "dishwasher_load"]:
        buttons = [
            [InlineKeyboardButton("\u2705 Я сделяль :)", callback_data=f"done_user|{task_key}")],
            [InlineKeyboardButton("\U0001F62D Отстань на 30 минут плз", callback_data=f"remind_30|{task_key}")],
        ]
    else:
        buttons = [[InlineKeyboardButton("\u2705 Готово", callback_data=f"done_user|{task_key}")]]
    return InlineKeyboardMarkup(buttons)

# Планирование задач
async def schedule_group_jobs(application: Application):
    if group_chat_id is None:
        logging.warning("Групповой chat_id не установлен. Напоминания не будут запланированы.")
        return
    for task_key, task in TASKS.items():
        application.job_queue.run_daily(
            send_reminder,
            time=time(task["hour"], task["minute"], tzinfo=local_tz),
            days=(0, 1, 2, 3, 4, 5, 6),
            data={"chat_id": group_chat_id, "task_key": task_key}
        )

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global group_chat_id
    group_chat_id = update.effective_chat.id
    await update.message.reply_text(
        "Привет! Я бот-напоминалка 😊 Буду каждый день напоминать группе о важных делах."
    )
    await schedule_group_jobs(context.application)

# Команда /list
async def task_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = []
    keyboard = []
    for key, task in TASKS.items():
        lines.append(f"📌 {task['name']}")
        keyboard.append([InlineKeyboardButton(task["name"], callback_data=f"view|{key}")])
    await update.message.reply_text(
        text="Список задач:\n" + "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
            text=f"🔔 Напоминание: {TASKS[task_key]['name']}",
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

# Пост-инициализация
async def post_init(application: Application):
    if group_chat_id:
        await schedule_group_jobs(application)

# Точка входа
if __name__ == '__main__':
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in environment variables")

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", task_list))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.post_init = post_init

    application.run_polling()
