import logging
from typing import Optional, Dict, Any, List
from .database import Database
from .content_storage import ContentStorage
from .referral_storage import ReferralStorage
from .ticket_storage import TicketStorage

logger = logging.getLogger(__name__)

class UserStorage:
    def __init__(self, database_url: str):
        self.db = Database(database_url)
        self.content_storage: Optional[ContentStorage] = None
        self.referral_storage: Optional[ReferralStorage] = None
        self.ticket_storage: Optional[TicketStorage] = None
    
    async def initialize(self):
        """Инициализирует все хранилища"""
        await self.db.connect()
        self.content_storage = ContentStorage(self.db)
        self.referral_storage = ReferralStorage(self.db)
        self.ticket_storage = TicketStorage(self.db)
        logger.info("✅ All storages initialized")
    
    async def close(self):
        """Закрывает подключение к базе данных"""
        await self.db.close()
    
    async def save_user_from_message(self, message) -> bool:
        """Сохраняет пользователя из сообщения Telegram"""
        user = message.from_user
        
        user_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language_code': user.language_code,
            'is_premium': getattr(user, 'is_premium', False)
        }
        
        return await self.db.add_or_update_user(user_data)
    
    async def get_thread_id(self, user_id: int) -> Optional[str]:
        """Получает thread_id для пользователя"""
        user = await self.db.get_user(user_id)
        return user.get('openai_thread_id') if user else None
    
    async def save_thread_id(self, user_id: int, thread_id: str) -> bool:
        """Сохраняет thread_id для пользователя"""
        return await self.db.update_openai_thread(user_id, thread_id)
    
    async def update_activity(self, user_id: int) -> bool:
        """Обновляет активность пользователя"""
        return await self.db.update_user_activity(user_id)
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает статистику пользователя"""
        return await self.db.get_user(user_id)
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получает всех пользователей"""
        return await self.db.get_all_users()
    
    async def get_active_users_count(self, days: int = 30) -> int:
        """Получает количество активных пользователей"""
        users = await self.db.get_active_users(days)
        return len(users)
    
    async def log_message(self, user_id: int, message_text: str, message_type: str, 
                         openai_thread_id: Optional[str] = None, 
                         openai_message_id: Optional[str] = None,
                         tokens_used: int = 0) -> bool:
        """Логирует сообщение"""
        return await self.db.add_message(
            user_id, message_text, message_type, 
            openai_thread_id, openai_message_id, tokens_used
        )
    
    async def log_openai_activity(self, user_id: int, thread_id: str, run_id: str, 
                                status: str, error_message: Optional[str] = None) -> bool:
        """Логирует активность OpenAI"""
        return await self.db.add_openai_activity(
            user_id, thread_id, run_id, status, error_message
        )
    
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Получает общую статистику бота"""
        return await self.db.get_user_stats()
    
    # Методы для работы с админами
    async def add_admin(self, user_id: int, username: str, first_name: str, added_by: int) -> bool:
        """Добавляет пользователя в список админов"""
        return await self.db.add_admin(user_id, username, first_name, added_by)
    
    async def remove_admin(self, user_id: int) -> bool:
        """Удаляет пользователя из списка админов"""
        return await self.db.remove_admin(user_id)
    
    async def is_admin(self, user_id: int) -> bool:
        """Проверяет является ли пользователь админом"""
        return await self.db.is_admin(user_id)
    
    async def get_all_admins(self) -> List[Dict[str, Any]]:
        """Получает список всех админов"""
        return await self.db.get_all_admins()
    
    async def is_super_admin(self, user_id: int) -> bool:
        """Проверяет является ли пользователь суперадмином"""
        from config import config
        return user_id == config.SUPER_ADMIN_ID
    
    # Методы для работы с токенами
    async def add_token_usage(self, user_id: int, thread_id: Optional[str], message_id: Optional[str], 
                             model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> bool:
        """Добавляет запись о использовании токенов"""
        return await self.db.add_token_usage(
            user_id, thread_id, message_id, model, 
            prompt_tokens, completion_tokens, total_tokens
        )
    
    async def get_user_token_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Получает статистику токенов для пользователя"""
        return await self.db.get_user_token_stats(user_id, days)
    
    async def get_global_token_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получает глобальную статистику токенов"""
        return await self.db.get_global_token_stats(days)

    # 🔥 МЕТОДЫ ДЛЯ КОНТЕНТА И РЕФЕРАЛОВ
    
    async def get_more_buttons(self) -> List[Dict]:
        """Получает все кнопки для /more"""
        if self.content_storage:
            return await self.content_storage.get_all_active_buttons()
        return []
    
    async def get_button_by_id(self, button_id: int) -> Optional[Dict]:
        """Получает кнопку по ID"""
        if self.content_storage:
            return await self.content_storage.get_button_by_id(button_id)
        return None
    
    async def get_button_by_command(self, command: str) -> Optional[Dict]:
        """Получает кнопку по команде"""
        if self.content_storage:
            return await self.content_storage.get_button_by_command(command)
        return None
    
    async def get_content_by_key(self, key: str) -> Optional[Dict]:
        """Получает контент по ключу"""
        if self.content_storage:
            return await self.content_storage.get_content_by_key(key)
        return None
    
    async def update_content(self, key: str, **kwargs) -> bool:
        """Обновляет контент"""
        if self.content_storage:
            return await self.content_storage.update_content(key, **kwargs)
        return False
    
    async def add_button(self, key: str, button_text: str, command: str, 
                        content_text: str, model: str = 'gpt-4.1', 
                        order_index: int = 0) -> bool:
        """Добавляет новую кнопку"""
        if self.content_storage:
            return await self.content_storage.add_button(
                key, button_text, command, content_text, model, order_index
            )
        return False

    # 🔥 МЕТОДЫ ДЛЯ СИСТЕМЫ ПОДДЕРЖКИ (ТИКЕТЫ)
    
    async def get_support_topics(self) -> List[Dict]:
        """Получает все темы поддержки из таблицы bot_content"""
        try:
            if not self.db.pool:
                logger.error("Database pool not initialized")
                return []
                
            query = """
                SELECT 
                    id,
                    key as name,
                    button_text,
                    content_text as description
                FROM bot_content 
                WHERE category = 'support_topics' AND is_active = TRUE
                ORDER BY order_index
            """
            rows = await self.db.pool.fetch(query)
            
            # 🔥 ИСПРАВЛЕНИЕ: парсим emoji из button_text
            topics = []
            for row in rows:
                topic = dict(row)
                button_text = topic['button_text']
                
                # Извлекаем emoji (первый символ) и текст
                emoji = button_text[0] if button_text and len(button_text) > 0 else '📝'
                name_text = button_text[1:].strip() if len(button_text) > 1 else button_text
                
                topics.append({
                    'id': topic['id'],
                    'name': topic['name'],
                    'button_text': name_text,  # текст без emoji ("Техническая проблема")
                    'emoji': emoji,            # первый символ как emoji ("🔧")
                    'description': topic.get('description', '')
                })
            
            logger.info(f"📋 Prepared {len(topics)} support topics")
            return topics
            
        except Exception as e:
            logger.error(f"❌ Error getting support topics: {e}")
            return []

    async def create_support_ticket(self, user_id: int, topic: str, message: str) -> Optional[str]:
        """Создает новый тикет поддержки"""
        try:
            import uuid
            from datetime import datetime
            
            ticket_number = f"TKT-{uuid.uuid4().hex[:8].upper()}"
            
            logger.info(f"🎫 Creating ticket: {ticket_number}, user: {user_id}, topic: {topic}")
            
            query = """
                INSERT INTO support_tickets 
                (ticket_number, user_id, topic, message, status, created_at)
                VALUES ($1, $2, $3, $4, 'open', $5)
                RETURNING ticket_number
            """
            
            result = await self.db.pool.fetchval(
                query, ticket_number, user_id, topic, message, datetime.now()
            )
            
            logger.info(f"✅ Support ticket created successfully: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error creating support ticket: {e}", exc_info=True)
            return None

    async def get_user_tickets(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Получает тикеты пользователя"""
        try:
            query = """
                SELECT ticket_number, topic, message as user_message, admin_response, 
                    status, created_at, updated_at
                FROM support_tickets 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """
            return await self.db.pool.fetch(query, user_id, limit)
        except Exception as e:
            logger.error(f"Error getting user tickets: {e}")
            return []

    # Методы для реферальной системы
    async def add_referral(self, referrer_id: int, referral_id: int, referral_code: str = None) -> bool:
        """Добавляет реферальную связь"""
        if self.referral_storage:
            return await self.referral_storage.add_referral(referrer_id, referral_id, referral_code)
        return False
    
    async def get_referrer(self, referral_id: int) -> Optional[int]:
        """Получает ID реферера"""
        if self.referral_storage:
            return await self.referral_storage.get_referrer(referral_id)
        return None
    
    async def get_referrals_count(self, referrer_id: int) -> int:
        """Получает количество рефералов"""
        if self.referral_storage:
            return await self.referral_storage.get_referrals_count(referrer_id)
        return 0
    
    async def get_referral_stats(self, referrer_id: int) -> Dict:
        """Получает статистику рефералов"""
        if self.referral_storage:
            return await self.referral_storage.get_referral_stats(referrer_id)

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ТИКЕТАМИ (ADMIN BOT) ====================
    
    async def get_ticket_by_number(self, ticket_number: str) -> Optional[Dict]:
        """Получает тикет по номеру"""
        if self.ticket_storage:
            return await self.ticket_storage.get_ticket_by_number(ticket_number)
        return None
    
    async def get_all_open_tickets(self) -> List[Dict]:
        """Получает все открытые тикеты"""
        if self.ticket_storage:
            return await self.ticket_storage.get_all_open_tickets()
        return []
    
    async def get_admin_tickets(self, admin_id: int) -> List[Dict]:
        """Получает тикеты админа"""
        if self.ticket_storage:
            return await self.ticket_storage.get_admin_tickets(admin_id)
        return []
    
    async def assign_ticket_to_admin(self, ticket_number: str, admin_id: int) -> bool:
        """Назначает тикет админу"""
        if self.ticket_storage:
            return await self.ticket_storage.assign_ticket_to_admin(ticket_number, admin_id)
        return False
    
    async def add_admin_reply(self, ticket_number: str, admin_id: int, reply_text: str) -> bool:
        """Добавляет ответ админа"""
        if self.ticket_storage:
            return await self.ticket_storage.add_admin_reply(ticket_number, admin_id, reply_text)
        return False
    
    async def close_ticket(self, ticket_number: str, admin_id: int) -> bool:
        """Закрывает тикет"""
        if self.ticket_storage:
            return await self.ticket_storage.close_ticket(ticket_number, admin_id)
        return False
    
    async def update_ticket_channel_message(
        self, 
        ticket_number: str, 
        message_id: int, 
        thread_id: Optional[int] = None
    ) -> bool:
        """Обновляет ID сообщения в канале"""
        if self.ticket_storage:
            return await self.ticket_storage.update_ticket_channel_message(
                ticket_number, message_id, thread_id
            )
        return False