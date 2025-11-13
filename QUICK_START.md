# ⚡ Быстрый старт

## 🚀 Автоматическое развертывание

```bash
cd /app
./deploy.sh
```

Скрипт автоматически:
- ✅ Проверит PostgreSQL
- ✅ Остановит старые боты
- ✅ Запустит User Bot
- ✅ Запустит Admin Bot
- ✅ Покажет статус и логи

---

## 📋 Основные команды

### Управление ботами

```bash
# Статус
supervisorctl status bots:*

# Запуск всех ботов
supervisorctl start bots:*

# Остановка всех ботов
supervisorctl stop bots:*

# Перезапуск всех ботов
supervisorctl restart bots:*

# Перезапуск только User Bot
supervisorctl restart bots:user_bot

# Перезапуск только Admin Bot
supervisorctl restart bots:admin_bot
```

### Просмотр логов

```bash
# User Bot - последние 50 строк
tail -50 /var/log/supervisor/user_bot.out.log

# Admin Bot - последние 50 строк
tail -50 /var/log/supervisor/admin_bot.out.log

# Мониторинг в реальном времени
tail -f /var/log/supervisor/user_bot.out.log

# Ошибки
tail -f /var/log/supervisor/user_bot.err.log
tail -f /var/log/supervisor/admin_bot.err.log
```

### Проверка базы данных

```bash
# Подключение к базе
sudo -u postgres psql -d telegram_bot

# Проверка таблиц
\dt

# Проверка тикетов
SELECT * FROM support_tickets ORDER BY created_at DESC LIMIT 5;

# Проверка админов
SELECT * FROM admins;

# Выход
\q
```

---

## 🔧 Быстрое решение проблем

### Бот не запускается

```bash
# Смотрим ошибки
tail -30 /var/log/supervisor/user_bot.err.log

# Проверяем PostgreSQL
service postgresql status
service postgresql start

# Перезапускаем бота
supervisorctl restart bots:user_bot
```

### Конфликт с другим ботом

```bash
# Находим процесс
ps aux | grep python | grep bot

# Останавливаем
kill <PID>

# Перезапускаем через supervisor
supervisorctl restart bots:*
```

### Бот не отвечает в Telegram

```bash
# Проверяем что бот запущен
supervisorctl status bots:user_bot

# Смотрим логи на ошибки
tail -50 /var/log/supervisor/user_bot.out.log
tail -50 /var/log/supervisor/user_bot.err.log

# Перезапускаем
supervisorctl restart bots:user_bot
```

---

## 📁 Структура файлов

```
/app/
├── user_bot/              # Основной бот
│   ├── main.py
│   ├── .env              # Конфигурация
│   └── app/
├── admin_bot/            # Админский бот
│   ├── main.py
│   ├── .env              # Конфигурация
│   └── app/
├── shared/               # Общие модули
│   └── storage/          # База данных
├── deploy.sh             # ⚡ Скрипт развертывания
├── QUICK_START.md        # 📋 Эта инструкция
└── DEPLOY_INSTRUCTIONS.md # 📚 Полная инструкция
```

---

## ⚙️ Конфигурация

### User Bot (.env)
```
TELEGRAM_TOKEN=7404722403:AAFm8MZDlhLoBMRtYlICDMNXyJ01U7TAdI4
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_bot
```

### Admin Bot (.env)
```
TELEGRAM_TOKEN=7763530661:AAFrnrbArarKPG_iCdPvreLZHrXee7ymsyE
ADMIN_CHANNEL_ID=-1002339461988
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_bot
```

---

## 📞 Контакты

- **User Bot:** @SlovaBoga_bot
- **Admin Bot:** (узнать после запуска в логах)
- **Админский канал:** https://t.me/+WLn4SNrLCjRiMDIy
- **Суперадмин ID:** 304631563

---

## 🆘 Нужна помощь?

📚 **Полная инструкция:** `/app/DEPLOY_INSTRUCTIONS.md`

Содержит:
- Подробное описание каждого шага
- Решение типичных проблем
- Настройка админского канала
- Тестирование workflow тикетов
