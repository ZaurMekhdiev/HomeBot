# bot.py — точка входа для Telegram-бота

"""
Этот файл служит точкой входа для запуска Telegram-бота.
Он отвечает за:
- Инициализацию базы данных
- Запуск планировщика задач (apscheduler)
- Регистрацию всех обработчиков команд, сообщений и кнопок
- Запуск основного цикла polling
"""

import asyncio
import nest_asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import TOKEN, TIMEZONE
from database.db import init_db, add_daily_tasks
from logic.scheduler import create_scheduler
from handlers import commands, callbacks, messages

async def main():
    # Добавляем системные задачи из logic.tasks в базу при старте
    add_daily_tasks()

    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    scheduler = create_scheduler()
    scheduler.start()

    app.add_handler(CommandHandler("start", commands.start))
    app.add_handler(CommandHandler("list", commands.task_list))
    app.add_handler(CommandHandler("list_daily", commands.list_daily))
    app.add_handler(CommandHandler("add_notify", commands.add_notify))
    app.add_handler(CommandHandler("debug", commands.debug))

    app.add_handler(CallbackQueryHandler(callbacks.notify_button_handler, pattern="^(day|time|custom_date)"))
    app.add_handler(CallbackQueryHandler(callbacks.button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages.handle_text))

    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())