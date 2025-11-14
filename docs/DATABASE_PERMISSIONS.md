# 🔐 Права доступа к базе данных PostgreSQL

## Проблема

При запуске ботов может возникнуть ошибка:
```
❌ Failed to connect to PostgreSQL: must be owner of table users
```

## Причина

Таблицы созданы от имени пользователя `postgres`, но боты подключаются как `bot_user`. Для выполнения некоторых операций (например, `ALTER TABLE`) требуется быть владельцем таблицы.

## ✅ Решение

### Автоматическое (при первой установке)

Наш скрипт `database/setup_database.sh` автоматически назначает `bot_user` владельцем всех таблиц. Используйте его:

```bash
cd database
sudo ./setup_database.sh
```

### Ручное исправление

Если проблема все еще возникает, выполните вручную:

```bash
sudo -u postgres psql -d telegram_bot << 'EOF'
-- Назначаем bot_user владельцем всех таблиц
ALTER TABLE users OWNER TO bot_user;
ALTER TABLE admins OWNER TO bot_user;
ALTER TABLE bot_content OWNER TO bot_user;
ALTER TABLE messages OWNER TO bot_user;
ALTER TABLE referrals OWNER TO bot_user;
ALTER TABLE support_tickets OWNER TO bot_user;
ALTER TABLE token_usage OWNER TO bot_user;

-- Назначаем владельца для всех sequences (автоинкрементных полей)
ALTER SEQUENCE messages_message_id_seq OWNER TO bot_user;
ALTER SEQUENCE token_usage_usage_id_seq OWNER TO bot_user;
ALTER SEQUENCE support_tickets_id_seq OWNER TO bot_user;
ALTER SEQUENCE referrals_referral_id_seq OWNER TO bot_user;
EOF
```

### Проверка прав

```bash
# Проверка владельцев таблиц
sudo -u postgres psql -d telegram_bot -c "\dt"

# Должно быть:
# Owner = bot_user для всех таблиц
```

Правильный вывод:
```
              List of relations
 Schema |      Name       | Type  |  Owner   
--------+-----------------+-------+----------
 public | admins          | table | bot_user
 public | bot_content     | table | bot_user
 public | messages        | table | bot_user
 public | referrals       | table | bot_user
 public | support_tickets | table | bot_user
 public | token_usage     | table | bot_user
 public | users           | table | bot_user
```

### Проверка прав на sequences

```bash
sudo -u postgres psql -d telegram_bot -c "\ds"

# Owner = bot_user для всех sequences
```

## 📋 Что делает наш SQL скрипт

Файл `database/02_create_tables.sql` содержит:

```sql
-- В конце файла:

-- Выдача прав bot_user на все таблицы
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bot_user;

-- Назначение bot_user владельцем всех таблиц
ALTER TABLE users OWNER TO bot_user;
ALTER TABLE messages OWNER TO bot_user;
ALTER TABLE token_usage OWNER TO bot_user;
ALTER TABLE bot_content OWNER TO bot_user;
ALTER TABLE admins OWNER TO bot_user;
ALTER TABLE support_tickets OWNER TO bot_user;
ALTER TABLE referrals OWNER TO bot_user;
```

## 🔍 Диагностика

### Проверка текущего пользователя

```bash
# Подключение от имени bot_user
psql -U bot_user -d telegram_bot -h localhost -W

# В psql:
SELECT current_user;
# Должно вернуть: bot_user
```

### Проверка прав

```bash
# Проверка прав bot_user на таблицы
sudo -u postgres psql -d telegram_bot -c "
SELECT 
    schemaname, 
    tablename, 
    tableowner 
FROM pg_tables 
WHERE schemaname = 'public';"
```

### Тест подключения бота

```python
# Тест из Python
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='bot_user',
        password='eyo3uZh8uWsrinldTe',
        database='telegram_bot'
    )
    
    # Попробуем выполнить операцию, требующую прав владельца
    try:
        await conn.execute("SELECT * FROM users LIMIT 1")
        print("✅ Подключение успешно!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    await conn.close()

asyncio.run(test())
```

## 🚨 Типичные ошибки

### 1. "Permission denied for table users"

**Причина:** bot_user не имеет прав на таблицу

**Решение:**
```bash
sudo -u postgres psql -d telegram_bot -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;"
```

### 2. "must be owner of table users"

**Причина:** bot_user не является владельцем таблицы

**Решение:**
```bash
sudo -u postgres psql -d telegram_bot -c "ALTER TABLE users OWNER TO bot_user;"
```

### 3. "permission denied for sequence"

**Причина:** bot_user не имеет прав на автоинкрементные поля

**Решение:**
```bash
sudo -u postgres psql -d telegram_bot -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bot_user;"
```

## 💡 Лучшие практики

1. **Всегда создавайте базу с правильным владельцем:**
   ```sql
   CREATE DATABASE telegram_bot OWNER bot_user;
   ```

2. **Создавайте таблицы от имени владельца базы:**
   ```bash
   psql -U bot_user -d telegram_bot -f create_tables.sql
   ```

3. **Используйте автоматические скрипты:**
   - Наш `setup_database.sh` делает все правильно
   - Не создавайте таблицы вручную от `postgres`

4. **Проверяйте права после каждого изменения:**
   ```bash
   sudo -u postgres psql -d telegram_bot -c "\dt"
   ```

## 📖 Дополнительная информация

### PostgreSQL Role vs User

- **Role** - это абстракция прав доступа
- **User** - это role с правом LOGIN
- `bot_user` - это user (role с LOGIN)

### GRANT vs ALTER TABLE OWNER

- **GRANT** - дает права на выполнение операций (SELECT, INSERT, UPDATE, DELETE)
- **ALTER TABLE OWNER** - делает пользователя владельцем, что дает ВСЕ права, включая ALTER, DROP

### Иерархия прав

```
Superuser (postgres)
    └── Database Owner
        └── Table Owner (bot_user) ← Наш бот
            └── Granted privileges
```

## ✅ Проверка после исправления

После применения исправлений:

1. **Перезапустите боты:**
   ```bash
   sudo supervisorctl restart user_bot admin_bot
   ```

2. **Проверьте логи:**
   ```bash
   sudo supervisorctl tail -f user_bot stdout
   ```

3. **Ожидаемый результат:**
   ```
   ✅ PostgreSQL connection pool initialized
   ✅ Bot dependencies initialized
   🚀 Bot started successfully
   ```

---

💡 **Совет:** Всегда используйте наш `setup_database.sh` для первичной установки - он делает все правильно!
