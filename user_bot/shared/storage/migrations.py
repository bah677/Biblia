"""
Database migrations for ticket system
"""
import asyncpg
import logging

logger = logging.getLogger(__name__)

async def migrate_support_tickets(database_url: str):
    """Добавляет новые поля для системы тикетов"""
    try:
        conn = await asyncpg.connect(database_url)
        
        # Добавляем новые поля к таблице support_tickets
        await conn.execute('''
            ALTER TABLE support_tickets 
            ADD COLUMN IF NOT EXISTS admin_id BIGINT,
            ADD COLUMN IF NOT EXISTS taken_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS channel_message_id BIGINT,
            ADD COLUMN IF NOT EXISTS channel_thread_id INTEGER,
            ADD COLUMN IF NOT EXISTS replied_at TIMESTAMP WITH TIME ZONE
        ''')
        
        logger.info("✅ Migration: support_tickets updated successfully")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
