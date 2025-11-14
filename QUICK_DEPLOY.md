# ⚡ Быстрое развертывание на боевом сервере

## Предварительные требования

- ✅ Ubuntu 20.04+ / Debian 11+
- ✅ Python 3.11+
- ✅ PostgreSQL 14+
- ✅ Git
- ✅ Токены Telegram ботов
- ✅ OpenAI API ключи

## 📋 Чеклист развертывания (10 минут)

### 1️⃣ Клонирование и подготовка (2 мин)

```bash
# Клонируйте репозиторий
git clone https://github.com/bah677/Biblia.git
cd Biblia

# Проверьте структуру
ls -la
# Должны быть: admin_bot/, user_bot/, shared/, database/, docs/
```

### 2️⃣ База данных (3 мин)

```bash
# Автоматическая установка PostgreSQL и создание БД
cd database
chmod +x setup_database.sh
sudo ./setup_database.sh
cd ..

# Скрипт выполнит:
# - Установку PostgreSQL
# - Создание пользователя bot_user
# - Создание базы telegram_bot
# - Создание всех таблиц
# - Назначение bot_user владельцем таблиц ⚡ (важно!)
# - Загрузку начальных данных
```

### 3️⃣ Конфигурация (1 мин)

**Создайте единый .env файл в корне:**
```bash
cd /path/to/Biblia
cp .env.example .env
nano .env
```

Заполните все переменные:
```env
# Telegram Bots
USER_BOT_TOKEN=ваш_токен_user_бота
ADMIN_BOT_TOKEN=ваш_токен_admin_бота

# OpenAI Keys
USER_OPENAI_API_KEY=ваш_openai_ключ_для_user_бота
ADMIN_OPENAI_API_KEY=ваш_openai_ключ_для_admin_бота
ASSISTANT_ID=ваш_assistant_id

# Database
DB_PASSWORD=eyo3uZh8uWsrinldTe

# Admin
SUPER_ADMIN_ID=ваш_telegram_id
ADMIN_CHANNEL_ID=-1003415479914
ADMIN_CHANNEL_THREAD_ID=2
ADMIN_CHANNEL_LINK=ваш_invite_link
```

💡 **Преимущество:** Все настройки в одном месте!

### 4️⃣ Установка зависимостей (2 мин)

```bash
# Python зависимости
cd /path/to/Biblia/user_bot
pip3 install -r requirements.txt

cd /path/to/Biblia/admin_bot
pip3 install -r requirements.txt
```

### 5️⃣ Настройка Supervisor (1 мин)

```bash
cd /path/to/Biblia
sudo cp supervisor_bots.conf /etc/supervisor/conf.d/

# ⚠️ ВАЖНО: Отредактируйте пути в конфиге
sudo nano /etc/supervisor/conf.d/supervisor_bots.conf
# Замените /home/alex/Biblia на ваш путь

# Перезагрузите Supervisor
sudo supervisorctl reread
sudo supervisorctl update
```

### 6️⃣ Запуск ботов (30 сек)

```bash
# Запуск через Supervisor (рекомендуется)
sudo supervisorctl start user_bot
sudo supervisorctl start admin_bot

# Проверка статуса
sudo supervisorctl status

# Ожидаемый результат:
# admin_bot    RUNNING   pid 12345, uptime 0:00:10
# user_bot     RUNNING   pid 12346, uptime 0:00:10
```

**Альтернативный запуск (без Supervisor):**
```bash
# В отдельных терминалах
python3 /path/to/Biblia/user_bot/main.py
python3 /path/to/Biblia/admin_bot/main.py
```

## 🧪 Проверка работоспособности

### User Bot
1. Найдите бота в Telegram
2. Отправьте `/start`
3. Проверьте команды: `/more`, `/support`, `/mytickets`

### Admin Bot
1. Найдите админ бота в Telegram
2. Отправьте `/start`
3. Проверьте команды: `/stats`, `/tickets`, `/list_admins`

### Проверка интеграции
1. Создайте тикет в User Bot через `/support`
2. Проверьте, что сообщение появилось в админ-группе
3. Перейдите по ссылке в Admin Bot
4. Возьмите тикет в работу
5. Убедитесь, что сообщение в группе обновилось

## 📊 Мониторинг

```bash
# Логи через Supervisor
sudo tail -f /var/log/supervisor/user_bot.out.log
sudo tail -f /var/log/supervisor/admin_bot.out.log

# Логи напрямую (если не Supervisor)
tail -f user_bot/logs/bot.log
tail -f admin_bot/logs/admin_bot.log

# Проверка процессов
ps aux | grep python | grep bot

# Проверка БД
sudo -u postgres psql -d telegram_bot -c "SELECT COUNT(*) FROM users;"
```

## 🔧 Управление

```bash
# Остановка
sudo supervisorctl stop user_bot admin_bot

# Перезапуск
sudo supervisorctl restart user_bot admin_bot

# Статус
sudo supervisorctl status

# Обновление кода
cd /path/to/Biblia
git pull origin main
sudo supervisorctl restart user_bot admin_bot
```

## ⚠️ Типичные проблемы

### Бот не запускается
```bash
# Проверьте логи
sudo supervisorctl tail -f user_bot stderr

# Проверьте права доступа
ls -la /path/to/Biblia/user_bot/main.py

# Проверьте путь к Python
which python3
```

### Ошибка подключения к БД
```bash
# Проверьте, что PostgreSQL работает
sudo systemctl status postgresql

# Проверьте пароль в .env файлах
grep DB_PASSWORD user_bot/.env admin_bot/.env

# Проверьте подключение
psql -U bot_user -d telegram_bot -h localhost -W
```

### Бот не отвечает
```bash
# Проверьте токен
grep TELEGRAM_TOKEN user_bot/.env

# Проверьте, что процесс запущен
ps aux | grep "user_bot/main.py"

# Перезапустите
sudo supervisorctl restart user_bot
```

## 📚 Дополнительные ресурсы

- **Полная документация:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Структура проекта:** [README.md](README.md)
- **Документация в папке:** [docs/](docs/)

## ✅ Завершение

После успешного развертывания у вас должно быть:

- ✅ 2 работающих бота (User Bot и Admin Bot)
- ✅ PostgreSQL база данных с таблицами
- ✅ Supervisor управляет процессами
- ✅ Интеграция с OpenAI работает
- ✅ Система тикетов работает
- ✅ Уведомления в админ-группу приходят

🎉 **Поздравляем! Развертывание завершено!**
