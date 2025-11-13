import asyncio
import logging
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

from app.bot.core import TelegramBot
from config import config

# Создаем папку для логов если её нет
os.makedirs('logs', exist_ok=True)

# Настройка форматера
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 1. ОБЩИЙ лог (все события)
general_handler = logging.FileHandler(
    filename='logs/general.log', 
    encoding='utf-8',
    mode='a'
)
general_handler.setFormatter(formatter)
general_handler.setLevel(logging.INFO)

# 2. Лог ЗАПУСКОВ (только запуски бота и пользователи)
startup_handler = logging.FileHandler(
    filename='logs/startup.log', 
    encoding='utf-8',
    mode='a'
)
startup_handler.setFormatter(formatter)
startup_handler.setLevel(logging.INFO)

# 3. Консоль (для разработки)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Настраиваем корневой логгер
logging.basicConfig(
    level=logging.INFO,
    handlers=[general_handler, startup_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Специальный логгер для событий запуска
startup_logger = logging.getLogger('startup')

async def main():
    bot = None
    try:
        # Логируем запуск бота в ОБОИХ файлах
        startup_logger.info("=" * 50)
        startup_logger.info("🚀 BOT STARTING")
        startup_logger.info(f"📅 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        startup_logger.info("=" * 50)
        
        logger.info("Validating configuration...")
        
        # Валидируем конфигурацию
        config.validate()
        logger.info("✅ Configuration validated successfully")
        
        # Создаем бота
        bot = TelegramBot()
        logger.info("🤖 Bot instance created")
        
        # Инициализируем зависимости бота
        logger.info("🔄 Initializing bot dependencies...")
        await bot.initialize()
        logger.info("✅ Bot dependencies initialized")
        
        # УДАЛЯЕМ ВЕБХУК перед запуском поллинга
        logger.info("🔄 Deleting webhook...")
        await bot.delete_webhook()
        logger.info("✅ Webhook deleted successfully")
        
        # Запускаем бота
        logger.info("🔄 Starting bot polling...")
        await bot.start()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        startup_logger.error(f"❌ Bot failed to start: {e}")
        
        # Корректно закрываем ресурсы если бот был создан
        if bot:
            await bot.close()
        
        sys.exit(1)
    
    finally:
        # Гарантированно закрываем ресурсы
        if bot:
            await bot.close()
        logger.info("✅ Bot shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())