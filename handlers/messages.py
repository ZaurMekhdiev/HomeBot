"""
handlers/messages.py — обработка текстовых сообщений от пользователей

Функции:
- handle_text: отвечает за обработку пользовательского ввода на разных этапах добавления задачи
- ask_time: отправляет клавиатуру выбора времени
"""

from datetime import datetime, time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import TIMEZONE
from database.db import save_user_task

user_pending_tasks = {}  # глобальный словарь задач для каждого chat_id

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    now = datetime.now(TIMEZONE)

    if context.user_data.get("awaiting_task_name"):
        task_name = update.message.text.strip()
        user_pending_tasks[chat_id] = {"task_name": task_name}
        context.user_data["awaiting_task_name"] = False

        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        keyboard = [[InlineKeyboardButton(day, callback_data=f"day|{i}")] for i, day in enumerate(days)]
        keyboard.append([InlineKeyboardButton("Ввести дату", callback_data="custom_date")])
        await update.message.reply_text("Када над?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif context.user_data.get("awaiting_date"):
        try:
            date_parts = list(map(int, update.message.text.strip().split()))
            if len(date_parts) != 3:
                raise ValueError
            reminder_date = datetime(date_parts[2], date_parts[1], date_parts[0], tzinfo=TIMEZONE)
            if reminder_date < now:
                await update.message.reply_text("Дата и время не могут быть в прошлом. Пожалуйста, введите корректную дату.")
                return
            task_info = user_pending_tasks.get(chat_id)
            if task_info:
                context.user_data["reminder_date"] = reminder_date
                context.user_data["awaiting_date"] = False
                await ask_time(update, context)
        except ValueError:
            await update.message.reply_text("Формат: ДД ММ ГГГГ, например: 17 05 2025")

    elif context.user_data.get("awaiting_time"):
        try:
            time_parts = list(map(int, update.message.text.strip().split(":")))
            if len(time_parts) != 2:
                raise ValueError
            reminder_time = time(time_parts[0], time_parts[1])
            reminder_date = context.user_data.get("reminder_date")
            if reminder_date:
                reminder_datetime = datetime.combine(reminder_date.date(), reminder_time, tzinfo=TIMEZONE)
                if reminder_datetime < now:
                    await update.message.reply_text("Дата и время не могут быть в прошлом. Пожалуйста, введите корректное время.")
                    return
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