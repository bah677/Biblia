# 🚀 НАЧНИТЕ ОТСЮДА

## Проект уже развернут и работает! ✅

Оба бота запущены на этом сервере через supervisor.

---

## 📋 ПОШАГОВАЯ ИНСТРУКЦИЯ ДЛЯ ВАШЕГО СЕРВЕРА:

### Шаг 1: Скопировать проект на ваш сервер

```bash
# На вашем сервере создайте директорию
mkdir -p /app

# Скопируйте весь проект из текущего сервера
# Используйте scp, rsync или git
```

### Шаг 2: Установить зависимости

```bash
# Подключитесь к вашему серверу по SSH
ssh your-server

# Перейдите в директорию проекта
cd /app

# Установите PostgreSQL (если не установлен)
apt-get update
apt-get install -y postgresql postgresql-contrib

# Запустите PostgreSQL
service postgresql start

# Установите Python зависимости
pip install -r /app/user_bot/requirements.txt
pip install -r /app/admin_bot/requirements.txt
```

### Шаг 3: Настроить базу данных

```bash
# Создайте пользователя базы данных
sudo -u postgres psql -c "CREATE USER bot_user WITH PASSWORD 'eyo3uZh8uWsrinldTe';"

# Создайте базу данных
sudo -u postgres psql -c "CREATE DATABASE telegram_bot OWNER bot_user;"

# Дайте права
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE telegram_bot TO bot_user;"

# Запустите создание таблиц
cd /app && python3 scripts/create_support_tickets_table.py

# Запустите миграции
cd /app && python3 run_migrations.py
```

### Шаг 4: Настроить .env файлы

Проверьте и при необходимости обновите:

**User Bot (.env):**
```bash
nano /app/user_bot/.env
```

**Admin Bot (.env):**
```bash
nano /app/admin_bot/.env
```

Убедитесь что:
- `DB_HOST=localhost` (если БД на том же сервере)
- Токены ботов указаны правильно
- Все остальные параметры корректны

### Шаг 5: Настроить Supervisor

```bash
# Скопируйте конфигурацию
cp /app/supervisor_bots.conf /etc/supervisor/conf.d/bots.conf

# Обновите supervisor
supervisorctl reread
supervisorctl update
```

### Шаг 6: Запустить боты

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

### Шаг 7: Проверить логи

```bash
# User Bot
tail -50 /var/log/supervisor/user_bot.out.log

# Admin Bot
tail -50 /var/log/supervisor/admin_bot.out.log

# Ошибки
tail -50 /var/log/supervisor/user_bot.err.log
tail -50 /var/log/supervisor/admin_bot.err.log
```

### Шаг 8: Добавить себя как админа

```bash
sudo -u postgres psql -d telegram_bot
```

В psql выполните:
```sql
INSERT INTO admins (user_id, username, first_name, added_by_admin_id, is_active, added_at)
VALUES (304631563, 'ваш_username', 'Ваше Имя', 304631563, true, NOW())
ON CONFLICT (user_id) DO NOTHING;
```

Выход: `\q`

### Шаг 9: Добавить Admin Bot в канал

1. Откройте https://t.me/+WLn4SNrLCjRiMDIy
2. Добавьте @SuperAdmin_MirOn_bot как администратора
3. Дайте права: публикация, редактирование, удаление сообщений

### Шаг 10: Протестировать

**User Bot:**
1. Откройте @SlovaBoga_bot
2. `/start`
3. `/support` → создайте тестовый тикет

**Admin Bot:**
1. Откройте @SuperAdmin_MirOn_bot
2. `/start`
3. `/tickets` → проверьте список тикетов

---

## 🔧 АЛЬТЕРНАТИВА: Автоматическое развертывание

Вместо ручных шагов можно использовать скрипт:

```bash
cd /app
./deploy.sh
```

Скрипт автоматически:
- Проверит PostgreSQL
- Остановит старые боты
- Запустит User Bot и Admin Bot
- Покажет статус и логи

---

## 📊 Управление после развертывания

### Основные команды:

```bash
# Статус
supervisorctl status bots:*

# Перезапуск всех
supervisorctl restart bots:*

# Перезапуск конкретного бота
supervisorctl restart bots:user_bot
supervisorctl restart bots:admin_bot

# Остановка
supervisorctl stop bots:*

# Запуск
supervisorctl start bots:*

# Просмотр логов
tail -f /var/log/supervisor/user_bot.out.log
tail -f /var/log/supervisor/admin_bot.out.log
```

---

## ⚠️ Важные моменты

1. **Остановите старый бот** перед запуском нового User Bot, иначе будет конфликт

2. **PostgreSQL должен быть запущен**:
   ```bash
   service postgresql status
   service postgresql start
   ```

3. **Проверьте что порт 5432 доступен**:
   ```bash
   netstat -an | grep 5432
   ```

4. **Убедитесь что .env файлы настроены правильно**

---

## 📚 Полная документация

- **Быстрый старт:** `/app/QUICK_START.md`
- **Инструкция по развертыванию:** `/app/DEPLOY_INSTRUCTIONS.md`
- **Итоговый отчет:** `/app/FINAL_SUMMARY.md`
- **Документация проекта:** `/app/README.md`

---

## 🆘 Нужна помощь?

Если что-то не работает:

1. Проверьте логи: `tail -50 /var/log/supervisor/<bot>.err.log`
2. Проверьте PostgreSQL: `service postgresql status`
3. Проверьте supervisor: `supervisorctl status`
4. Перезапустите: `supervisorctl restart bots:*`

---

## 🤖 Контакты ботов

- **User Bot:** @SlovaBoga_bot
- **Admin Bot:** @SuperAdmin_MirOn_bot
- **Канал:** https://t.me/+WLn4SNrLCjRiMDIy
- **Суперадмин:** ID 304631563

---

## 🎉 Готово!

После выполнения всех шагов оба бота будут работать на вашем сервере!
