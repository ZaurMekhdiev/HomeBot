"""
handlers/commands.py — содержит обработчики команд Telegram-бота

Функции:
- /start — приветственное сообщение
- /list — заглушка для списка задач
- /list_daily — заглушка для задач на сегодня
- /add_notify — начало добавления задачи
- /debug — отладочная информация
"""

from telegram import Update
from telegram.ext import ContextTypes

user_pending_tasks = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот-напоминалка 😊 Используй /add_notify чтобы добавить задачу.")

async def task_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здесь будет список всех задач (в разработке)")

async def list_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здесь будет список задач на сегодня (в разработке)")

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"DEBUG: {context.user_data}")

async def add_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("Че над?))))))) (введи название задачи)")
    context.user_data['awaiting_task_name'] = True
