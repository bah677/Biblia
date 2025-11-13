#!/bin/bash

echo "================================"
echo "  Setting up Telegram Bot Project"
echo "================================"
echo ""

# Проверяем PostgreSQL
echo "Checking PostgreSQL..."
sudo service postgresql status
if [ $? -ne 0 ]; then
    echo "Starting PostgreSQL..."
    sudo service postgresql start
fi

# Устанавливаем зависимости для User Bot
echo ""
echo "Installing User Bot dependencies..."
cd /app/user_bot
pip install -q -r requirements.txt

# Устанавливаем зависимости для Admin Bot
echo "Installing Admin Bot dependencies..."
cd /app/admin_bot
pip install -q -r requirements.txt

# Создаем директории для логов
echo ""
echo "Creating log directories..."
mkdir -p /app/user_bot/logs
mkdir -p /app/admin_bot/logs

# Копируем supervisor конфиг
echo "Setting up Supervisor..."
sudo cp /app/supervisor_bots.conf /etc/supervisor/conf.d/bots.conf

# Перезагружаем supervisor
sudo supervisorctl reread
sudo supervisorctl update

echo ""
echo "================================"
echo "  Setup Complete!"
echo "================================"
echo ""
echo "Available commands:"
echo "  sudo supervisorctl status        - Check status"
echo "  sudo supervisorctl start user_bot   - Start user bot"
echo "  sudo supervisorctl start admin_bot  - Start admin bot"
echo "  sudo supervisorctl start bots:*     - Start all bots"
echo "  sudo supervisorctl restart bots:*   - Restart all bots"
echo ""
echo "Logs:"
echo "  User Bot:  tail -f /app/user_bot/logs/general.log"
echo "  Admin Bot: tail -f /app/admin_bot/logs/admin_bot.log"
echo ""
