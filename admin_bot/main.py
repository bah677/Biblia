import asyncio
import logging
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app.bot.admin_core import AdminBot
from config import config

os.makedirs('logs', exist_ok=True)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

admin_handler = logging.FileHandler(
    filename='logs/admin_bot.log', 
    encoding='utf-8',
    mode='a'
)
admin_handler.setFormatter(formatter)
admin_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    handlers=[admin_handler, console_handler]
)

logger = logging.getLogger(__name__)

async def main():
    bot = None
    try:
        logger.info("=" * 50)
        logger.info("ADMIN BOT STARTING")
        logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        config.validate()
        logger.info("Configuration validated successfully")
        
        bot = AdminBot()
        logger.info("Admin bot instance created")
        
        await bot.initialize()
        logger.info("Admin bot dependencies initialized")
        
        await bot.bot.delete_webhook()
        logger.info("Webhook deleted successfully")
        
        await bot.start()
        
    except Exception as e:
        logger.error(f"Failed to start admin bot: {e}", exc_info=True)
        
        if bot:
            await bot.close()
        
        sys.exit(1)
    
    finally:
        if bot:
            await bot.close()
        logger.info("Admin bot shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
