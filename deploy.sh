#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🚀 Развертывание User Bot & Admin Bot                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода успеха
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Функция для вывода ошибки
error() {
    echo -e "${RED}❌ $1${NC}"
}

# Функция для вывода предупреждения
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Шаг 1: Проверка PostgreSQL
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 1: Проверка PostgreSQL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if service postgresql status > /dev/null 2>&1; then
    success "PostgreSQL запущен"
else
    warning "PostgreSQL не запущен, запускаем..."
    service postgresql start
    if [ $? -eq 0 ]; then
        success "PostgreSQL успешно запущен"
    else
        error "Не удалось запустить PostgreSQL"
        exit 1
    fi
fi

# Шаг 2: Поиск старого бота
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 2: Поиск и остановка старого бота"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

OLD_BOT_PID=$(ps aux | grep -E "python.*main.py" | grep -v grep | grep -v deploy | awk '{print $2}')

if [ -n "$OLD_BOT_PID" ]; then
    warning "Найден старый бот (PID: $OLD_BOT_PID)"
    echo "Остановить его? (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        kill $OLD_BOT_PID
        sleep 2
        success "Старый бот остановлен"
    else
        warning "Старый бот НЕ остановлен - могут быть конфликты!"
    fi
else
    success "Старых ботов не найдено"
fi

# Шаг 3: Проверка supervisor
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 3: Проверка конфигурации Supervisor"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "/etc/supervisor/conf.d/bots.conf" ]; then
    success "Конфигурация supervisor найдена"
else
    error "Конфигурация supervisor не найдена!"
    exit 1
fi

# Перезагружаем конфигурацию
supervisorctl reread > /dev/null 2>&1
supervisorctl update > /dev/null 2>&1
success "Конфигурация supervisor обновлена"

# Шаг 4: Запуск User Bot
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 4: Запуск User Bot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

supervisorctl stop bots:user_bot > /dev/null 2>&1
sleep 2
supervisorctl start bots:user_bot

sleep 3

STATUS=$(supervisorctl status bots:user_bot | awk '{print $2}')
if [ "$STATUS" = "RUNNING" ]; then
    success "User Bot запущен и работает"
    echo ""
    echo "Последние строки логов:"
    tail -15 /var/log/supervisor/user_bot.out.log
else
    error "User Bot не запустился!"
    echo ""
    echo "Ошибки:"
    tail -20 /var/log/supervisor/user_bot.err.log
    exit 1
fi

# Шаг 5: Запуск Admin Bot
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Шаг 5: Запуск Admin Bot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

supervisorctl stop bots:admin_bot > /dev/null 2>&1
sleep 2
supervisorctl start bots:admin_bot

sleep 3

STATUS=$(supervisorctl status bots:admin_bot | awk '{print $2}')
if [ "$STATUS" = "RUNNING" ]; then
    success "Admin Bot запущен и работает"
    echo ""
    echo "Последние строки логов:"
    tail -15 /var/log/supervisor/admin_bot.out.log
else
    error "Admin Bot не запустился!"
    echo ""
    echo "Ошибки:"
    tail -20 /var/log/supervisor/admin_bot.err.log
    exit 1
fi

# Шаг 6: Итоговый статус
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Итоговый статус"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

supervisorctl status bots:*

echo ""
success "Развертывание завершено!"
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  📝 Следующие шаги:                                        ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  1. Проверьте User Bot в Telegram (@SlovaBoga_bot)        ║"
echo "║  2. Добавьте себя как админа (см. инструкцию)             ║"
echo "║  3. Проверьте Admin Bot в Telegram                         ║"
echo "║  4. Добавьте Admin Bot в канал как администратора          ║"
echo "║  5. Создайте тестовый тикет для проверки                   ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  📚 Полная инструкция: /app/DEPLOY_INSTRUCTIONS.md        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Мониторинг логов:"
echo "   User Bot:  tail -f /var/log/supervisor/user_bot.out.log"
echo "   Admin Bot: tail -f /var/log/supervisor/admin_bot.out.log"
echo ""
echo "🔧 Управление:"
echo "   Перезапуск: supervisorctl restart bots:*"
echo "   Остановка:  supervisorctl stop bots:*"
echo "   Статус:     supervisorctl status bots:*"
echo ""
