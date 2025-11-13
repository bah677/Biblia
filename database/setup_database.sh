#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  📊 Настройка базы данных PostgreSQL                      ║"
echo "║  Biblia Telegram Bot Project                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Проверка PostgreSQL
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 1: Проверка PostgreSQL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v psql &> /dev/null; then
    success "PostgreSQL установлен"
else
    error "PostgreSQL не установлен!"
    echo "Установите: sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi

if service postgresql status > /dev/null 2>&1; then
    success "PostgreSQL запущен"
else
    warning "PostgreSQL не запущен, запускаем..."
    sudo service postgresql start
    if [ $? -eq 0 ]; then
        success "PostgreSQL запущен"
    else
        error "Не удалось запустить PostgreSQL"
        exit 1
    fi
fi

# Создание базы данных и пользователя
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 2: Создание базы данных и пользователя"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo -u postgres psql << 'EOSQL'
-- Создание пользователя
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bot_user') THEN
        CREATE ROLE bot_user WITH LOGIN PASSWORD 'eyo3uZh8uWsrinldTe';
    END IF;
END
$$;

-- Создание базы данных
SELECT 'CREATE DATABASE telegram_bot OWNER bot_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'telegram_bot')\gexec

-- Выдача прав
GRANT ALL PRIVILEGES ON DATABASE telegram_bot TO bot_user;
EOSQL

if [ $? -eq 0 ]; then
    success "База данных и пользователь созданы"
else
    error "Ошибка при создании базы данных"
    exit 1
fi

# Создание таблиц
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 3: Создание таблиц"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo -u postgres psql -d telegram_bot -f /app/database/02_create_tables.sql > /dev/null 2>&1

if [ $? -eq 0 ]; then
    success "Таблицы созданы"
else
    error "Ошибка при создании таблиц"
    exit 1
fi

# Вставка начальных данных
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 4: Вставка начальных данных"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo -u postgres psql -d telegram_bot -f /app/database/03_insert_initial_data.sql > /dev/null 2>&1

if [ $? -eq 0 ]; then
    success "Начальные данные добавлены"
else
    warning "Возможно данные уже существуют"
fi

# Проверка таблиц
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 5: Проверка созданных таблиц"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
sudo -u postgres psql -d telegram_bot -c "\dt"

echo ""
success "База данных полностью настроена!"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  📊 Информация для подключения:                           ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  Host:     localhost                                       ║"
echo "║  Port:     5432                                            ║"
echo "║  Database: telegram_bot                                    ║"
echo "║  User:     bot_user                                        ║"
echo "║  Password: eyo3uZh8uWsrinldTe                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
