## 📁 Структура проекта

```bash
.
├── bot.py                   # Точка входа
├── config.py                # Конфигурация (таймзона, токен и т.д.)
├── requirements.txt         # pip зависимости
├── reminders.db             # SQLite база
├── bot.log                  # Логи
├── README.md                # Этот файл
│
├── database/
│   └── db.py                # Инициализация и операции с БД
│
├── handlers/
│   ├── callbacks.py         # Обработка inline-кнопок
│   ├── commands.py          # Команды Telegram (/start, /add_notify)
│   └── messages.py          # Обработка текстовых сообщений
│
├── logic/
│   ├── scheduler.py         # Планировщик задач (apscheduler)
│   └── tasks.py             # Предустановленные задачи
```
