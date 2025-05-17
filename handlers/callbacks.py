"""
handlers/callbacks.py — обработчики inline-кнопок Telegram-бота

Функции:
- notify_button_handler: обработка кнопок выбора дня, даты и времени
- button_handler: заглушка для нераспознанных кнопок
"""

from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from config import TIMEZONE
from database.db import save_user_task
from handlers.messages import ask_time, user_pending_tasks


async def notify_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data
    now = datetime.now(TIMEZONE)

    if data.startswith("day"):
        _, day_index = data.split("|")
        day_index = int(day_index)
        days_ahead = (day_index - now.weekday()) % 7
        reminder_date = now + timedelta(days=days_ahead)
        task_info = user_pending_tasks.get(chat_id)
        if task_info:
            context.user_data["reminder_date"] = reminder_date
            await ask_time(update, context)

    elif data == "custom_date":
        await query.edit_message_text("Введите дату в формате: ДД ММ ГГГГ, например: 17 05 2025")
        context.user_data["awaiting_date"] = True

    elif data.startswith("time"):
        _, time_str = data.split("|")
        reminder_time = datetime.strptime(time_str, "%H:%M").time()
        reminder_date = context.user_data.get("reminder_date")
        if reminder_date:
            reminder_datetime = datetime.combine(reminder_date.date(), reminder_time, tzinfo=TIMEZONE)
            if reminder_datetime < now:
                await query.edit_message_text("Дата и время не могут быть в прошлом. Попробуйте снова.")
                return
            task_info = user_pending_tasks.get(chat_id)
            if task_info:
                save_user_task(chat_id, task_info["task_name"], reminder_datetime)
                await query.edit_message_text("Задача добавлена!")
                user_pending_tasks.pop(chat_id, None)
                context.user_data["awaiting_time"] = False


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Кнопка пока ничего не делает")
