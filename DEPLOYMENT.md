# 🚀 Подробная инструкция по развертыванию на сервере

## 📋 Требования

- **Сервер:** Ubuntu 20.04+ / Debian 11+
- **Python:** 3.10+
- **PostgreSQL:** 12+
- **RAM:** минимум 1GB
- **Права:** root или sudo доступ

---

## 📥 Шаг 1: Подготовка сервера

### 1.1. Подключитесь к серверу

```bash
ssh root@144.124.239.159
# или
ssh alex@144.124.239.159
```

### 1.2. Обновите систему

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 1.3. Установите необходимые пакеты

```bash
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    git \
    supervisor
```

---

## 🗄️ Шаг 2: Настройка PostgreSQL

### 2.1. Запустите PostgreSQL

```bash
sudo service postgresql start
sudo service postgresql status
```

Должно быть: **online**

### 2.2. Создайте базу данных АВТОМАТИЧЕСКИ

```bash
cd /app/database
sudo chmod +x setup_database.sh
sudo ./setup_database.sh
```

Этот скрипт автоматически:
- ✅ Создаст пользователя `bot_user`
- ✅ Создаст базу данных `telegram_bot`
- ✅ Создаст все таблицы
- ✅ Назначит `bot_user` владельцем всех таблиц (важно!)
- ✅ Добавит начальные данные
- ✅ Настроит права доступа

### 2.3. Или создайте базу ВРУЧНУЮ

Если автоматический скрипт не сработал:

```bash
# Создание пользователя и базы
sudo -u postgres psql << 'EOF'
CREATE USER bot_user WITH PASSWORD 'eyo3uZh8uWsrinldTe';
CREATE DATABASE telegram_bot OWNER bot_user;
GRANT ALL PRIVILEGES ON DATABASE telegram_bot TO bot_user;
\q
EOF

# Создание таблиц
sudo -u postgres psql -d telegram_bot -f /app/database/02_create_tables.sql

# Вставка данных
sudo -u postgres psql -d telegram_bot -f /app/database/03_insert_initial_data.sql
```

### 2.4. Проверка базы данных

```bash
sudo -u postgres psql -d telegram_bot
```

В psql выполните:
```sql
-- Проверка таблиц
\dt

-- Проверка данных
SELECT COUNT(*) FROM bot_content;
-- Должно быть: 17 (13 для /more + 4 для /support)

-- Проверка прав
\du bot_user

-- Выход
\q
```

---

## 📂 Шаг 3: Клонирование проекта

### 3.1. Клонируйте репозиторий

```bash
cd /
sudo git clone https://github.com/bah677/Biblia.git app
cd /app
```

### 3.2. Проверьте структуру

```bash
ls -la
```

Должно быть:
```
user_bot/
admin_bot/
shared/
database/
scripts/
README.md
.gitignore
```

---

## 🔑 Шаг 4: Настройка конфигурации

### 4.1. Создайте .env для User Bot

```bash
cd /app/user_bot
cp .env.example .env
nano .env
```

Заполните:
```env
# User Bot Telegram Token (получить у @BotFather)
TELEGRAM_TOKEN=ваш_токен_user_бота

# OpenAI API Key (с platform.openai.com)
OPENAI_API_KEY=ваш_openai_ключ
ASSISTANT_ID=ваш_assistant_id

# PostgreSQL Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_bot
DB_USER=bot_user
DB_PASSWORD=eyo3uZh8uWsrinldTe

# Super Admin (ваш Telegram ID)
SUPER_ADMIN_ID=ваш_telegram_id

# Admin Bot Token
ADMIN_BOT_TOKEN=токен_админского_бота
ADMIN_CHANNEL_ID=-1001234567890
ADMIN_CHANNEL_THREAD_ID=2

# Settings
LOG_LEVEL=INFO
MAX_WORKERS=5
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

### 4.2. Создайте .env для Admin Bot

```bash
cd /app/admin_bot
cp .env.example .env
nano .env
```

Заполните:
```env
# Admin Bot Telegram Token
TELEGRAM_TOKEN=токен_админского_бота

# OpenAI (опционально, для статистики)
OPENAI_API_KEY=ваш_openai_ключ

# PostgreSQL Database (те же данные что в User Bot)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_bot
DB_USER=bot_user
DB_PASSWORD=eyo3uZh8uWsrinldTe

# Super Admin
SUPER_ADMIN_ID=ваш_telegram_id

# Admin Group
ADMIN_CHANNEL_ID=-1001234567890
ADMIN_CHANNEL_THREAD_ID=2
ADMIN_CHANNEL_LINK=https://t.me/ваша_группа

# Settings
LOG_LEVEL=INFO
MAX_WORKERS=5
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## 🔧 Шаг 5: Создание пользователя (если нужно)

### 5.1. Создайте пользователя alex

```bash
# От root
sudo useradd -m -s /bin/bash alex
sudo passwd alex
# Введите пароль дважды

# Проверка
id alex
```

### 5.2. Передайте права на проект

```bash
sudo chown -R alex:alex /app/user_bot /app/admin_bot /app/shared
```

---

## 📦 Шаг 6: Установка Python зависимостей

### 6.1. Создайте виртуальное окружение

```bash
# От пользователя alex
su - alex
python3 -m venv /home/alex/.venv
```

### 6.2. Установите зависимости

```bash
# User Bot
cd /app/user_bot
/home/alex/.venv/bin/pip install -r requirements.txt

# Admin Bot
cd /app/admin_bot
/home/alex/.venv/bin/pip install -r requirements.txt
```

---

## ⚙️ Шаг 7: Настройка Supervisor

### 7.1. Скопируйте конфигурацию

```bash
sudo cp /app/supervisor_bots.conf /etc/supervisor/conf.d/bots.conf
```

### 7.2. Обновите пути в конфигурации

Откройте файл:
```bash
sudo nano /etc/supervisor/conf.d/bots.conf
```

Проверьте что указано:
```ini
[program:user_bot]
command=/home/alex/.venv/bin/python3 main.py
directory=/app/user_bot
user=alex

[program:admin_bot]
command=/home/alex/.venv/bin/python3 main.py
directory=/app/admin_bot
user=alex
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

### 7.3. Перезагрузите Supervisor

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

---

## 🚀 Шаг 8: Запуск ботов

### 8.1. Остановите старые боты (если есть)

```bash
# Найдите старые процессы
ps aux | grep python | grep bot

# Остановите их
kill <PID>
```

### 8.2. Запустите новые боты

```bash
sudo supervisorctl start bots:*
```

### 8.3. Проверьте статус

```bash
sudo supervisorctl status bots:*
```

Должно быть:
```
bots:admin_bot    RUNNING   pid 1234, uptime 0:00:15
bots:user_bot     RUNNING   pid 5678, uptime 0:00:30
```

### 8.4. Проверьте логи

```bash
# User Bot
tail -50 /var/log/supervisor/user_bot.out.log

# Admin Bot
tail -50 /var/log/supervisor/admin_bot.out.log

# Ошибки
tail -50 /var/log/supervisor/user_bot.err.log
tail -50 /var/log/supervisor/admin_bot.err.log
```

Не должно быть ошибок! ✅

---

## 👥 Шаг 9: Добавление администратора

### 9.1. Добавьте себя как админа

```bash
sudo -u postgres psql -d telegram_bot
```

В psql:
```sql
-- Замените данные на свои
INSERT INTO admins (user_id, username, first_name, added_by_admin_id, is_active, added_at)
VALUES (304631563, 'BakharevAleks', 'Alexey', 304631563, true, NOW())
ON CONFLICT (user_id) DO NOTHING;

-- Проверка
SELECT * FROM admins;

-- Выход
\q
```

---

## 📱 Шаг 10: Настройка Telegram

### 10.1. Получите токены ботов

**User Bot:**
1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Название: `Biblia User Bot`
4. Username: `YourBot_bot`
5. Скопируйте токен → в `/app/user_bot/.env`

**Admin Bot:**
1. Повторите процесс для админского бота
2. Название: `Biblia Admin Bot`
3. Username: `YourAdminBot_bot`
4. Скопируйте токен → в `/app/admin_bot/.env`

### 10.2. Получите OpenAI ключ

1. Зайдите на [platform.openai.com](https://platform.openai.com)
2. Перейдите в **API keys**
3. Нажмите **Create new secret key**
4. Скопируйте ключ → в оба `.env` файла

### 10.3. Создайте OpenAI Assistant

1. Зайдите на [platform.openai.com/assistants](https://platform.openai.com/assistants)
2. Нажмите **Create**
3. Имя: `Bible Assistant`
4. Инструкции: опишите как отвечать на вопросы
5. Модель: `gpt-4o` или `gpt-4`
6. Скопируйте `Assistant ID` → в `/app/user_bot/.env`

### 10.4. Узнайте свой Telegram ID

1. Откройте [@userinfobot](https://t.me/userinfobot)
2. Отправьте `/start`
3. Скопируйте ваш `Id` → в оба `.env` как `SUPER_ADMIN_ID`

### 10.5. Создайте админскую группу

1. Создайте группу в Telegram
2. Включите **Темы** (Topics) в настройках
3. Создайте топик для тикетов (например "Поддержка")
4. Добавьте Admin Bot в группу как **администратора**
5. Дайте права: публикация, редактирование, удаление
6. Узнайте ID группы и топика:
   - Перешлите сообщение из группы боту [@userinfobot](https://t.me/userinfobot)
   - Скопируйте `Id` группы → `ADMIN_CHANNEL_ID`
   - ID топика посмотрите в URL темы

---

## 🔄 Шаг 11: Перезапуск ботов

После изменения `.env` файлов:

```bash
sudo supervisorctl restart bots:*
```

Проверьте логи:
```bash
tail -f /var/log/supervisor/user_bot.out.log
tail -f /var/log/supervisor/admin_bot.out.log
```

---

## ✅ Шаг 12: Проверка работоспособности

### 12.1. User Bot

Откройте бота в Telegram и попробуйте:

```
/start - Приветствие
/more - 13 кнопок с темами
/support - Создание тикета
/mytickets - Просмотр тикетов
/affiliate - Реферальная система
```

### 12.2. Admin Bot

Откройте админского бота в Telegram:

```
/start - Приветствие
/tickets - Список тикетов
/stats - Статистика
/token_stats - Статистика токенов
/list_admins - Список админов
```

### 12.3. Создайте тестовый тикет

1. В User Bot отправьте `/support`
2. Выберите тему
3. Опишите проблему
4. Получите номер тикета

### 12.4. Проверьте админскую группу

- Должно прийти уведомление о новом тикете
- С deep link для взятия в работу
- БЕЗ превью ссылки

### 12.5. Проверьте Admin Bot

1. Кликните по ссылке из группы
2. Должен открыться Admin Bot с деталями тикета
3. Попробуйте взять тикет в работу
4. Проверьте что в группе обновился статус
5. Закройте тикет
6. Проверьте что сообщение удалилось из группы

---

## 🔧 Управление ботами

### Основные команды Supervisor

```bash
# Проверка статуса
sudo supervisorctl status bots:*

# Запуск
sudo supervisorctl start bots:*

# Остановка
sudo supervisorctl stop bots:*

# Перезапуск всех
sudo supervisorctl restart bots:*

# Перезапуск конкретного бота
sudo supervisorctl restart bots:user_bot
sudo supervisorctl restart bots:admin_bot
```

### Просмотр логов

```bash
# User Bot - последние 50 строк
tail -50 /var/log/supervisor/user_bot.out.log

# Admin Bot - последние 50 строк
tail -50 /var/log/supervisor/admin_bot.out.log

# Мониторинг в реальном времени
tail -f /var/log/supervisor/user_bot.out.log
tail -f /var/log/supervisor/admin_bot.out.log

# Оба одновременно
tail -f /var/log/supervisor/user_bot.out.log /var/log/supervisor/admin_bot.out.log

# Ошибки
tail -f /var/log/supervisor/user_bot.err.log
tail -f /var/log/supervisor/admin_bot.err.log
```

---

## 🗄️ Работа с базой данных

### Подключение к базе

```bash
sudo -u postgres psql -d telegram_bot
```

### Полезные команды

```sql
-- Список таблиц
\dt

-- Структура таблицы
\d support_tickets

-- Список пользователей
SELECT user_id, username, first_name, created_at FROM users ORDER BY created_at DESC LIMIT 10;

-- Список тикетов
SELECT ticket_number, status, topic, user_id, admin_id, created_at 
FROM support_tickets 
ORDER BY created_at DESC 
LIMIT 10;

-- Список админов
SELECT user_id, username, first_name, is_active FROM admins;

-- Статистика
SELECT status, COUNT(*) as count FROM support_tickets GROUP BY status;

-- Выход
\q
```

### Бэкап базы данных

```bash
# Создание бэкапа
sudo -u postgres pg_dump telegram_bot > /backup/telegram_bot_$(date +%Y%m%d).sql

# Восстановление из бэкапа
sudo -u postgres psql telegram_bot < /backup/telegram_bot_20250113.sql
```

---

## 🛡️ Безопасность

### Настройка файрволла

```bash
# Разрешить только SSH
sudo ufw allow 22/tcp

# Включить файрволл
sudo ufw enable

# Проверить статус
sudo ufw status
```

### Настройка PostgreSQL (опционально)

Если PostgreSQL должен быть доступен удаленно:

```bash
sudo nano /etc/postgresql/15/main/postgresql.conf
```

Найдите и измените:
```
listen_addresses = 'localhost'  # только локальные подключения
```

```bash
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

Убедитесь что есть:
```
local   all             all                                     peer
host    telegram_bot    bot_user        127.0.0.1/32           md5
```

Перезапустите PostgreSQL:
```bash
sudo service postgresql restart
```

---

## 🚨 Решение проблем

### Боты не запускаются

```bash
# Проверьте логи ошибок
tail -50 /var/log/supervisor/user_bot.err.log
tail -50 /var/log/supervisor/admin_bot.err.log

# Проверьте .env файлы
cat /app/user_bot/.env
cat /app/admin_bot/.env

# Проверьте права на файлы
ls -la /app/user_bot
ls -la /app/admin_bot

# Исправьте права если нужно
sudo chown -R alex:alex /app/user_bot /app/admin_bot /app/shared
```

### PostgreSQL недоступен

```bash
# Проверьте статус
sudo service postgresql status

# Запустите
sudo service postgresql start

# Проверьте порт
sudo netstat -tulpn | grep 5432

# Проверьте подключение
psql -U bot_user -d telegram_bot -h localhost
```

### Конфликт ботов

```bash
# Ошибка: "terminated by other getUpdates request"
# Значит где-то уже запущен бот с этим токеном

# Найдите процесс
ps aux | grep python | grep bot

# Остановите
kill <PID>

# Или через screen/tmux
screen -ls
screen -r <session>
# Ctrl+C для остановки

# Перезапустите через supervisor
sudo supervisorctl restart bots:*
```

### Бот не отвечает в Telegram

```bash
# 1. Проверьте что бот запущен
sudo supervisorctl status bots:user_bot

# 2. Проверьте логи на ошибки
tail -50 /var/log/supervisor/user_bot.err.log

# 3. Проверьте токен
# Отправьте тестовый запрос
curl -s "https://api.telegram.org/bot<ВАШ_ТОКЕН>/getMe" | jq

# 4. Перезапустите
sudo supervisorctl restart bots:user_bot
```

### Ошибка подключения к базе

```bash
# Проверьте что PostgreSQL запущен
sudo service postgresql status

# Проверьте пользователя и базу
sudo -u postgres psql -l | grep telegram_bot

# Проверьте права
sudo -u postgres psql -d telegram_bot -c "\du bot_user"

# Переустановите права
sudo -u postgres psql -d telegram_bot << 'EOF'
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bot_user;
EOF
```

---

## 📊 Мониторинг

### Автоматический перезапуск

Supervisor автоматически перезапускает упавшие боты (настроено `autorestart=true`)

### Просмотр статуса

```bash
# Быстрая проверка
sudo supervisorctl status

# Детальная информация
ps aux | grep alex | grep python
```

### Мониторинг логов

```bash
# Следите за логами в реальном времени
tail -f /var/log/supervisor/user_bot.out.log /var/log/supervisor/admin_bot.out.log

# Или используйте multitail (если установлен)
multitail /var/log/supervisor/user_bot.out.log /var/log/supervisor/admin_bot.out.log
```

---

## 🔄 Обновление проекта

### Обновление из GitHub

```bash
cd /app
git pull origin main

# Установите новые зависимости (если есть)
/home/alex/.venv/bin/pip install -r user_bot/requirements.txt
/home/alex/.venv/bin/pip install -r admin_bot/requirements.txt

# Перезапустите
sudo supervisorctl restart bots:*
```

---

## 📋 Чек-лист развертывания

- [ ] PostgreSQL установлен и запущен
- [ ] База данных `telegram_bot` создана
- [ ] Все таблицы созданы (8 таблиц)
- [ ] Начальные данные загружены (17 записей в bot_content)
- [ ] Пользователь `alex` создан
- [ ] Виртуальное окружение создано
- [ ] Зависимости установлены
- [ ] `.env` файлы настроены (User Bot + Admin Bot)
- [ ] Supervisor настроен
- [ ] Боты запущены и работают
- [ ] Вы добавлены как админ в базе
- [ ] Admin Bot добавлен в группу
- [ ] Тестовый тикет создан и работает
- [ ] Логи без ошибок

---

## 🎉 Готово!

После выполнения всех шагов оба бота будут работать на вашем сервере!

**Контакты:**
- User Bot: @YourBot_bot
- Admin Bot: @YourAdminBot_bot
- Группа: ваша админская группа

---

## 🆘 Поддержка

Если возникли проблемы:
1. Проверьте **все чек-листы** выше
2. Посмотрите **логи ошибок**
3. Убедитесь что **все .env файлы заполнены**
4. Проверьте что **PostgreSQL работает**
5. Убедитесь что **Supervisor запущен**

---

## 📚 Дополнительная документация

- `README.md` - Общая информация о проекте
- `database/` - SQL скрипты
- `docs/` - Дополнительная документация
