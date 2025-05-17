# logic/scheduler.py

"""
logic/scheduler.py — настройка планировщика APScheduler
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import TIMEZONE
from database.db import add_daily_tasks

def create_scheduler():
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(add_daily_tasks, 'cron', hour=0, minute=1)
    return scheduler
