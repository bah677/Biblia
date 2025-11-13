-- ============================================
-- Скрипт инициализации базы данных
-- Biblia Telegram Bot Project
-- ============================================

-- Создание базы данных
CREATE DATABASE IF NOT EXISTS telegram_bot
    ENCODING 'UTF8'
    LC_COLLATE 'en_US.UTF-8'
    LC_CTYPE 'en_US.UTF-8';

-- Подключение к базе
\c telegram_bot;

-- Создание пользователя для бота
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bot_user') THEN
        CREATE ROLE bot_user WITH LOGIN PASSWORD 'eyo3uZh8uWsrinldTe';
    END IF;
END
$$;

-- Выдача прав на базу данных
GRANT ALL PRIVILEGES ON DATABASE telegram_bot TO bot_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bot_user;

-- Настройка прав по умолчанию для будущих объектов
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO bot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO bot_user;

\echo '✅ База данных и пользователь созданы'
