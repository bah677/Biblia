# 🚀 Инструкция по развертыванию для пользователя alex

## ✅ Что сделано на текущем сервере:

1. **Создан пользователь alex** с паролем `hD1_cmp$ybycg5`
2. **Все файлы проекта** принадлежат alex:alex
3. **Оба бота запущены** от пользователя alex
4. **Виртуальное окружение** создано в `/home/alex/.venv`

---

## 📋 ИНСТРУКЦИЯ ДЛЯ ВАШЕГО СЕРВЕРА (144.124.239.159):

### Шаг 1: Подключитесь как alex

```bash
# С вашего компьютера
ssh alex@144.124.239.159
```

Пароль: `hD1_cmp$ybycg5`

### Шаг 2: Проверьте что проект скопирован

```bash
ls -la /app/
```

Должны быть папки:
- `/app/user_bot/`
- `/app/admin_bot/`
- `/app/shared/`

### Шаг 3: Проверьте владельца файлов

```bash
ls -la /app/ | grep -E "user_bot|admin_bot|shared"
```

Должно быть `alex alex` (если нет - выполните от root: `chown -R alex:alex /app/user_bot /app/admin_bot /app/shared`)

### Шаг 4: Создайте виртуальное окружение

```bash
# От пользователя alex
python3 -m venv /home/alex/.venv
```

### Шаг 5: Установите зависимости

```bash
# Установите базовые библиотеки
/home/alex/.venv/bin/pip install asyncpg python-dotenv aiogram openai aiohttp

# Установите зависимости User Bot
cd /app/user_bot
/home/alex/.venv/bin/pip install -r requirements.txt

# Установите зависимости Admin Bot
cd /app/admin_bot
/home/alex/.venv/bin/pip install -r requirements.txt
```

### Шаг 6: Настройте PostgreSQL (от root)

```bash
# Переключитесь на root
su -
# или
sudo -i

# Создайте пользователя БД
sudo -u postgres psql -c "CREATE USER bot_user WITH PASSWORD 'eyo3uZh8uWsrinldTe';"

# Создайте базу данных
sudo -u postgres psql -c "CREATE DATABASE telegram_bot OWNER bot_user;"

# Дайте права
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE telegram_bot TO bot_user;"

# Создайте таблицы
cd /app
python3 scripts/create_support_tickets_table.py

# Запустите миграции
cd /app
python3 run_migrations.py

# Создайте таблицу bot_content
sudo -u postgres psql -d telegram_bot -c "CREATE TABLE IF NOT EXISTS bot_content (
    id SERIAL PRIMARY KEY,
    content_type TEXT NOT NULL,
    content_key TEXT NOT NULL,
    emoji TEXT,
    button_text TEXT,
    content_data JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(content_type, content_key)
);"

# Добавьте тестовые темы поддержки
sudo -u postgres psql -d telegram_bot -c "INSERT INTO bot_content (content_type, content_key, emoji, button_text) VALUES 
('support_topic', 'general', '❓', 'Общий вопрос'),
('support_topic', 'technical', '🔧', 'Техническая проблема'),
('support_topic', 'payment', '💳', 'Вопрос по оплате'),
('support_topic', 'suggestion', '💡', 'Предложение')
ON CONFLICT DO NOTHING;"
```

### Шаг 7: Обновите .env файлы

**User Bot:**
```bash
nano /app/user_bot/.env
```

Проверьте/обновите:
```
TELEGRAM_TOKEN=7404722403:AAFm8MZDlhLoBMRtYlICDMNXyJ01U7TAdI4
OPENAI_API_KEY=<ваш_актуальный_ключ>
ASSISTANT_ID=asst_sK8jUyCCnSIAL6XqL0CSEwFi
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_bot
DB_USER=bot_user
DB_PASSWORD=eyo3uZh8uWsrinldTe
SUPER_ADMIN_ID=304631563
```

**Admin Bot:**
```bash
nano /app/admin_bot/.env
```

Проверьте:
```
TELEGRAM_TOKEN=7763530661:AAFrnrbArarKPG_iCdPvreLZHrXee7ymsyE
ADMIN_CHANNEL_ID=-1002339461988
ADMIN_CHANNEL_LINK=https://t.me/+WLn4SNrLCjRiMDIy
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_bot
DB_USER=bot_user
DB_PASSWORD=eyo3uZh8uWsrinldTe
SUPER_ADMIN_ID=304631563
```

### Шаг 8: Настройте Supervisor (от root)

```bash
# Скопируйте конфигурацию
cp /app/supervisor_bots.conf /etc/supervisor/conf.d/bots.conf

# Проверьте что в конфиге указан user=alex:
cat /etc/supervisor/conf.d/bots.conf | grep user=

# Должно быть: user=alex

# Обновите supervisor
supervisorctl reread
supervisorctl update
```

### Шаг 9: Запустите боты

```bash
# Запустите оба бота
supervisorctl start bots:*

# Проверьте статус
supervisorctl status bots:*
```

Должно быть:
```
bots:admin_bot    RUNNING   pid 1234, uptime 0:00:15
bots:user_bot     RUNNING   pid 5678, uptime 0:00:30
```

### Шаг 10: Проверьте процессы

```bash
ps aux | grep alex | grep python
```

Должны быть 2 процесса python от пользователя alex

### Шаг 11: Проверьте логи

```bash
# User Bot
tail -50 /var/log/supervisor/user_bot.out.log

# Admin Bot
tail -50 /var/log/supervisor/admin_bot.out.log

# Ошибки
tail -50 /var/log/supervisor/user_bot.err.log
tail -50 /var/log/supervisor/admin_bot.err.log
```

### Шаг 12: Добавьте себя как админа

```bash
sudo -u postgres psql -d telegram_bot
```

В psql:
```sql
INSERT INTO admins (user_id, username, first_name, added_by_admin_id, is_active, added_at)
VALUES (304631563, 'BakharevAleks', 'Alexey', 304631563, true, NOW())
ON CONFLICT (user_id) DO NOTHING;
```

Выход: `\q`

### Шаг 13: Протестируйте

**User Bot:**
- Откройте @SlovaBoga_bot
- `/start`
- `/support`
- `/mytickets`

**Admin Bot:**
- Откройте @SuperAdmin_MirOn_bot
- `/start`
- `/stats`
- `/tickets`

---

## 🔧 Управление (от пользователя alex или root)

```bash
# Статус
supervisorctl status bots:*

# Перезапуск
supervisorctl restart bots:*

# Остановка
supervisorctl stop bots:*

# Запуск
supervisorctl start bots:*

# Логи в реальном времени
tail -f /var/log/supervisor/user_bot.out.log
tail -f /var/log/supervisor/admin_bot.out.log
```

---

## 📁 Важные файлы и пути

```
/app/user_bot/.env                          # Конфигурация User Bot
/app/admin_bot/.env                         # Конфигурация Admin Bot
/home/alex/.venv/                           # Виртуальное окружение Python
/etc/supervisor/conf.d/bots.conf            # Supervisor конфигурация
/var/log/supervisor/user_bot.out.log        # Логи User Bot
/var/log/supervisor/admin_bot.out.log       # Логи Admin Bot
```

---

## ⚠️ Важно!

1. **Все команды supervisor** можно выполнять как от root, так и от alex
2. **PostgreSQL** должен быть запущен: `service postgresql status`
3. **Файлы проекта** должны принадлежать alex:alex
4. **Виртуальное окружение** должно быть в `/home/alex/.venv`

---

## 🆘 Решение проблем

### Боты не запускаются

```bash
# Проверьте права доступа
ls -la /app/user_bot /app/admin_bot

# Должно быть: alex alex

# Если нет - исправьте (от root):
chown -R alex:alex /app/user_bot /app/admin_bot /app/shared

# Проверьте логи ошибок
tail -50 /var/log/supervisor/user_bot.err.log
```

### PostgreSQL недоступен

```bash
service postgresql status
service postgresql start
```

### Конфликт с другим ботом

```bash
# Найдите процессы
ps aux | grep python | grep bot

# Остановите через supervisor
supervisorctl stop bots:*

# Или убейте процесс
kill <PID>
```

---

## 🎉 Готово!

После выполнения всех шагов оба бота будут работать на вашем сервере от пользователя alex!

**Контакты ботов:**
- User Bot: @SlovaBoga_bot
- Admin Bot: @SuperAdmin_MirOn_bot
- Канал: https://t.me/+WLn4SNrLCjRiMDIy
