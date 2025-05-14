import os
import logging
from datetime import time, timedelta
from typing import Dict

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
tasks = {
    "garden_morning": {"name": "Полить цветы в саду (утро)", "hour": 9, "minute": 0},
    "garden_evening": {"name": "Полить цветы в саду (вечер)", "hour": 20, "minute": 0},
    "spray_plants": {"name": "Растения хотят водички - спрей цветов! :)", "hour": 13, "minute": 0},
    "dishwasher_unload": {"name": "Разгрузи посудомойку", "hour": 10, "minute": 0},
    "dishwasher_load": {"name": "Загрузи посудомойку", "hour": 20, "minute": 0},
}

# Сохраняем chat_id и задачи
user_chats: Dict[int, dict] = {}
task_status: Dict[int, Dict[str, Dict[str, int]]] = {}

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_chats[chat_id] = {"tasks": tasks}
    task_status[chat_id] = {key: {"done": 0, "skips": 0} for key in tasks}

    await update.message.reply_text(
        "Привет! Я бот-напоминалка 😊 Буду каждый день напоминать тебе о важных делах."
    )

# Обработчик команды /list
async def task_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in task_status:
        await update.message.reply_text("Нет информации о задачах. Используйте /start.")
        return

    for task_key, task in tasks.items():
        status = task_status[chat_id].get(task_key, {"done": 0, "skips": 0})
        is_done = status["done"] == 1
        status_text = "✅ выполнено" if is_done else "❌ не выполнено"
        keyboard = []

        if is_done:
            keyboard = [
                [InlineKeyboardButton("🔁 Отметить как НЕ выполнено", callback_data=f"undo|{task_key}")]
            ]
        else:
            if task_key in ["garden_morning", "garden_evening"]:
                keyboard = [
                    [InlineKeyboardButton("🌧 Быф дождяф🌧", callback_data=f"done_rain|{task_key}")],
                    [InlineKeyboardButton("✅ Я полив :)", callback_data=f"done_user|{task_key}")],
                    [InlineKeyboardButton("😴 Отстань на 30 минут плз", callback_data=f"remind_30|{task_key}")],
                ]
            elif task_key == "spray_plants":
                keyboard = [
                    [InlineKeyboardButton("✅ Я сделяль :)", callback_data=f"done_user|{task_key}")],
                    [InlineKeyboardButton("😴 Отстань на 30 минут плз", callback_data=f"remind_30|{task_key}")],
                ]
            elif task_key in ["dishwasher_unload", "dishwasher_load"]:
                keyboard = [
                    [InlineKeyboardButton("✅ Я сделяль :)", callback_data=f"done_user|{task_key}")],
                    [InlineKeyboardButton("😴 Отстань на 30 минут плз", callback_data=f"remind_30|{task_key}")],
                ]
            else:
                keyboard = [[InlineKeyboardButton("✅ Готово", callback_data=f"done_user|{task_key}")]]

        header = "\n\nВыполнено <3\n" if is_done else ""

        await update.message.reply_text(
            text=f"📌 {task['name']}{header}Статус: {status_text}, отложено: {status['skips']} раз(а)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Отправка напоминания
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    task_key = job_data['task_key']
    task = tasks[task_key]

    if chat_id not in task_status:
        task_status[chat_id] = {}
    if task_key not in task_status[chat_id]:
        task_status[chat_id][task_key] = {"done": 0, "skips": 0}
    task_status[chat_id][task_key]["done"] = 0

    if task_key in ["garden_morning", "garden_evening"]:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌧 Быф дождяф🌧", callback_data=f"done_rain|{task_key}")],
            [InlineKeyboardButton("✅ Я полив :)", callback_data=f"done_user|{task_key}")],
            [InlineKeyboardButton("😴 Отстань на 30 минут плз", callback_data=f"remind_30|{task_key}")],
        ])
    elif task_key == "spray_plants":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я сделяль :)", callback_data=f"done_user|{task_key}")],
            [InlineKeyboardButton("😴 Отстань на 30 минут плз", callback_data=f"remind_30|{task_key}")],
        ])
    elif task_key in ["dishwasher_unload", "dishwasher_load"]:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я сделяль :)", callback_data=f"done_user|{task_key}")],
            [InlineKeyboardButton("😴 Отстань на 30 минут плз", callback_data=f"remind_30|{task_key}")],
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Готово", callback_data=f"done_user|{task_key}")]
        ])

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 Напоминание: {task['name']}",
        reply_markup=keyboard
    )

# Обработка нажатий кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data_parts = query.data.split('|')
    action = data_parts[0]
    task_key = data_parts[1]
    task = tasks[task_key]
    chat_id = query.message.chat.id

    if chat_id not in task_status:
        task_status[chat_id] = {}
    if task_key not in task_status[chat_id]:
        task_status[chat_id][task_key] = {"done": 0, "skips": 0}

    if action == "done_rain":
        task_status[chat_id][task_key]["done"] = 1
        await query.edit_message_text("🌧 Дождь полив :)")
    elif action == "done_user":
        task_status[chat_id][task_key]["done"] = 1
        await query.edit_message_text("✅ Пасиба))))")
    elif action == "remind_30":
        task_status[chat_id][task_key]["skips"] += 1
        await query.edit_message_text("🔁 Напомню через 30 минут")
        context.job_queue.run_once(
            send_reminder,
            when=timedelta(minutes=30),
            data={"chat_id": chat_id, "task_key": task_key}
        )
    elif action == "undo":
        task_status[chat_id][task_key]["done"] = 0
        await query.edit_message_text(f"❌ Задача '{task['name']}' снова активна")

# Планирование задач на каждый день
async def schedule_jobs(application: Application):
    job_queue: JobQueue = application.job_queue

    for chat_id in user_chats:
        for task_key, task in tasks.items():
            job_queue.run_daily(
                send_reminder,
                time=time(task["hour"], task["minute"], tzinfo=local_tz),
                days=(0, 1, 2, 3, 4, 5, 6),
                data={"chat_id": chat_id, "task_key": task_key}
            )

if __name__ == '__main__':
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in environment variables")

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", task_list))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.post_init = schedule_jobs

    application.run_polling()