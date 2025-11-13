"""
Helper для уведомления админского бота о новых тикетах
"""
import logging
import aiohttp
import os

logger = logging.getLogger(__name__)

class AdminNotifier:
    """Отправляет уведомления админскому боту"""
    
    def __init__(self, admin_bot_token: str):
        self.admin_bot_token = admin_bot_token
        self.api_url = f"https://api.telegram.org/bot{admin_bot_token}"
    
    async def notify_new_ticket(self, ticket: dict):
        """Уведомляет админский бот о новом тикете"""
        try:
            # Получаем информацию о боте для deep link
            async with aiohttp.ClientSession() as session:
                # Получаем username бота
                async with session.get(f"{self.api_url}/getMe") as response:
                    if response.status == 200:
                        data = await response.json()
                        bot_username = data['result']['username']
                        
                        # Формируем deep link
                        deep_link = f"https://t.me/{bot_username}?start=ticket_{ticket['ticket_number']}"
                        
                        logger.info(f"✅ New ticket {ticket['ticket_number']} ready for admin bot")
                        logger.info(f"Deep link: {deep_link}")
                        
                        return True
                    else:
                        logger.error(f"Failed to get admin bot info: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Error notifying admin bot: {e}")
            return False
