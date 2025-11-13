import logging
import time
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from .database import Database

logger = logging.getLogger(__name__)

class ContentStorage:
    def __init__(self, database: Database):
        self.db = database
        self.logger = logger
    
    async def get_content_by_key(self, key: str) -> Optional[Dict]:
        """Получает контент по ключу"""
        try:
            query = "SELECT * FROM bot_content WHERE key = $1 AND is_active = TRUE"
            row = await self.db.pool.fetchrow(query, key)
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Failed to get content by key {key}: {e}")
            return None
    
    async def get_all_active_buttons(self) -> List[Dict]:
        """Получает все активные кнопки для /more из таблицы bot_content"""
        try:
            query = """
                SELECT 
                    id,
                    key,
                    button_text,
                    command, 
                    content_text,
                    model,
                    order_index,
                    is_active
                FROM bot_content 
                WHERE category = 'more_buttons' AND is_active = TRUE
                ORDER BY order_index
            """
            rows = await self.db.pool.fetch(query)
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Failed to get active buttons: {e}")
            return []
    
    async def get_button_by_id(self, button_id: int) -> Optional[Dict]:
        """Получает кнопку по ID"""
        try:
            query = "SELECT * FROM bot_content WHERE id = $1 AND is_active = true"
            row = await self.db.pool.fetchrow(query, button_id)
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Error getting button by id {button_id}: {e}")
            return None
    
    async def get_button_by_command(self, command: str) -> Optional[Dict]:
        """Получает кнопку по команде"""
        try:
            query = """
                SELECT 
                    id,
                    key,
                    button_text,
                    command,
                    content_text,
                    model,
                    order_index
                FROM bot_content 
                WHERE command = $1 AND is_active = TRUE
            """
            row = await self.db.pool.fetchrow(query, command)
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Failed to get button by command {command}: {e}")
            return None
    
    async def add_button(self, key: str, button_text: str, command: str, 
                        content_text: str, model: str = 'gpt-4.1', 
                        order_index: int = 0) -> bool:
        """Добавляет новую кнопку в таблицу bot_content"""
        try:
            query = """
                INSERT INTO bot_content 
                (key, button_text, command, content_text, model, order_index, category, is_active, content_type)
                VALUES ($1, $2, $3, $4, $5, $6, 'more_buttons', TRUE, 'prompt')
                ON CONFLICT (key) DO UPDATE SET
                    button_text = EXCLUDED.button_text,
                    command = EXCLUDED.command,
                    content_text = EXCLUDED.content_text,
                    model = EXCLUDED.model,
                    order_index = EXCLUDED.order_index,
                    is_active = TRUE
            """
            await self.db.pool.execute(
                query, key, button_text, command, content_text, model, order_index
            )
            self.logger.info(f"✅ Button added/updated: {key}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to add button {key}: {e}")
            return False
    
    async def update_content(self, key: str, **kwargs) -> bool:
        """Обновляет контент"""
        try:
            set_parts = []
            values = []
            i = 1
            
            for field, value in kwargs.items():
                set_parts.append(f"{field} = ${i}")
                values.append(value)
                i += 1
            
            values.append(key)
            query = f"UPDATE bot_content SET {', '.join(set_parts)} WHERE key = ${i}"
            
            await self.db.pool.execute(query, *values)
            self.logger.info(f"✅ Content updated: {key}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to update content {key}: {e}")
            return False
    
    async def log_button_click(self, user_id: int, button_key: str, button_text: str) -> bool:
        """Логирует нажатие кнопки"""
        try:
            query = """
                INSERT INTO button_clicks (user_id, button_key, button_text)
                VALUES ($1, $2, $3)
            """
            await self.db.pool.execute(query, user_id, button_key, button_text)
            self.logger.info(f"📊 Button click logged: user_id={user_id}, button={button_key}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to log button click: {e}")
            return False
    
    async def get_button_stats(self, days: int = 30) -> Dict:
        """Получает статистику нажатий кнопок"""
        try:
            # Общая статистика
            total_stats_query = """
                SELECT 
                    COUNT(*) as total_clicks,
                    COUNT(DISTINCT user_id) as unique_users
                FROM button_clicks 
                WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
            """
            total_stats = await self.db.pool.fetchrow(total_stats_query, str(days))
            
            # Статистика по кнопкам
            button_stats_query = """
                SELECT 
                    button_key,
                    button_text,
                    COUNT(*) as click_count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM button_clicks 
                WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
                GROUP BY button_key, button_text
                ORDER BY click_count DESC
            """
            button_stats = await self.db.pool.fetch(button_stats_query, str(days))
            
            return {
                'total': dict(total_stats) if total_stats else {},
                'buttons': [dict(row) for row in button_stats]
            }
        except Exception as e:
            self.logger.error(f"❌ Failed to get button stats: {e}")
            return {}

    async def get_support_topics(self) -> List[Dict]:
        """Получает все активные темы поддержки из таблицы bot_content"""
        try:
            query = """
                SELECT 
                    id,
                    key as name,
                    button_text as emoji,
                    content_text as description,
                    order_index,
                    is_active
                FROM bot_content 
                WHERE category = 'support_topics' AND is_active = TRUE 
                ORDER BY order_index, id
            """
            rows = await self.db.pool.fetch(query)
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Failed to get support topics: {e}")
            return []
    
    async def create_support_ticket(self, user_id: int, topic: str, message: str) -> Optional[str]:
        """Создает тикет поддержки и возвращает номер тикета"""
        try:
            ticket_number = f"TKT-{uuid.uuid4().hex[:8].upper()}"
            
            query = """
                INSERT INTO support_tickets 
                (user_id, ticket_number, topic, user_message, status, created_at)
                VALUES ($1, $2, $3, $4, 'open', $5)
            """
            
            await self.db.pool.execute(
                query, user_id, ticket_number, topic, message, datetime.now()
            )
            
            self.logger.info(f"✅ Support ticket created: {ticket_number} for user_id={user_id}")
            return ticket_number
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create support ticket: {e}")
            return None
    
    async def get_user_tickets(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получает тикеты пользователя"""
        try:
            query = """
                SELECT 
                    ticket_number, 
                    topic, 
                    user_message, 
                    admin_response, 
                    status, 
                    created_at, 
                    updated_at
                FROM support_tickets 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """
            rows = await self.db.pool.fetch(query, user_id, limit)
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"❌ Failed to get user tickets: {e}")
            return []
    
    async def get_ticket_by_number(self, ticket_number: str) -> Optional[Dict]:
        """Получает тикет по номеру"""
        try:
            query = """
                SELECT 
                    ticket_number, 
                    topic, 
                    user_message, 
                    admin_response, 
                    status, 
                    created_at, 
                    updated_at, 
                    user_id
                FROM support_tickets 
                WHERE ticket_number = $1
            """
            row = await self.db.pool.fetchrow(query, ticket_number)
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"❌ Failed to get ticket {ticket_number}: {e}")
            return None
    
    async def update_ticket_status(self, ticket_number: str, status: str, admin_id: int = None, admin_response: str = None) -> bool:
        """Обновляет статус тикета"""
        try:
            query = """
                UPDATE support_tickets 
                SET status = $1, admin_id = $2, admin_response = $3, updated_at = NOW()
                WHERE ticket_number = $4
            """
            await self.db.pool.execute(query, status, admin_id, admin_response, ticket_number)
            
            self.logger.info(f"✅ Ticket {ticket_number} status updated to {status}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to update ticket status: {e}")
            return False