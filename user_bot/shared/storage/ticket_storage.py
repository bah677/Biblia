"""
Extended ticket management methods for admin bot
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class TicketStorage:
    """Методы для работы с тикетами (расширение для UserStorage)"""
    
    def __init__(self, db):
        self.db = db
    
    async def get_ticket_by_number(self, ticket_number: str) -> Optional[Dict]:
        """Получает тикет по номеру"""
        try:
            query = """
                SELECT * FROM support_tickets 
                WHERE ticket_number = $1
            """
            row = await self.db.pool.fetchrow(query, ticket_number)
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting ticket: {e}")
            return None
    
    async def get_all_open_tickets(self) -> List[Dict]:
        """Получает все открытые и в работе тикеты"""
        try:
            query = """
                SELECT * FROM support_tickets 
                WHERE status IN ('open', 'in_progress')
                ORDER BY created_at DESC
            """
            rows = await self.db.pool.fetch(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting open tickets: {e}")
            return []
    
    async def get_admin_tickets(self, admin_id: int) -> List[Dict]:
        """Получает тикеты, взятые конкретным админом"""
        try:
            query = """
                SELECT * FROM support_tickets 
                WHERE admin_id = $1 AND status IN ('in_progress', 'resolved')
                ORDER BY taken_at DESC
            """
            rows = await self.db.pool.fetch(query, admin_id)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting admin tickets: {e}")
            return []
    
    async def assign_ticket_to_admin(self, ticket_number: str, admin_id: int) -> bool:
        """Назначает тикет админу"""
        try:
            from datetime import datetime
            
            query = """
                UPDATE support_tickets 
                SET admin_id = $1, 
                    taken_at = $2, 
                    status = 'in_progress'
                WHERE ticket_number = $3 AND status = 'open'
                RETURNING ticket_number
            """
            result = await self.db.pool.fetchval(
                query, admin_id, datetime.now(), ticket_number
            )
            return result is not None
        except Exception as e:
            logger.error(f"Error assigning ticket: {e}")
            return False
    
    async def add_admin_reply(self, ticket_number: str, admin_id: int, reply_text: str) -> bool:
        """Добавляет ответ админа на тикет"""
        try:
            from datetime import datetime
            
            query = """
                UPDATE support_tickets 
                SET admin_response = $1, 
                    replied_at = $2,
                    admin_id = $3,
                    status = 'in_progress'
                WHERE ticket_number = $4
                RETURNING ticket_number
            """
            result = await self.db.pool.fetchval(
                query, reply_text, datetime.now(), admin_id, ticket_number
            )
            return result is not None
        except Exception as e:
            logger.error(f"Error adding admin reply: {e}")
            return False
    
    async def close_ticket(self, ticket_number: str, admin_id: int) -> bool:
        """Закрывает тикет"""
        try:
            query = """
                UPDATE support_tickets 
                SET status = 'closed', 
                    updated_at = NOW()
                WHERE ticket_number = $1 AND admin_id = $2
                RETURNING ticket_number
            """
            result = await self.db.pool.fetchval(query, ticket_number, admin_id)
            return result is not None
        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
            return False
    
    async def update_ticket_channel_message(
        self, 
        ticket_number: str, 
        message_id: int, 
        thread_id: Optional[int] = None
    ) -> bool:
        """Обновляет ID сообщения в канале"""
        try:
            query = """
                UPDATE support_tickets 
                SET channel_message_id = $1, 
                    channel_thread_id = $2
                WHERE ticket_number = $3
                RETURNING ticket_number
            """
            result = await self.db.pool.fetchval(
                query, message_id, thread_id, ticket_number
            )
            return result is not None
        except Exception as e:
            logger.error(f"Error updating channel message: {e}")
            return False
