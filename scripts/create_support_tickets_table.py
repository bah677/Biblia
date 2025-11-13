#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.storage.database import Database
from config import config

async def create_support_tickets_table():
    db = Database(config.database_url)
    await db.connect()
    
    try:
        print("🔄 Creating support_tickets table...")
        
        # Создаем таблицу support_tickets
        await db.pool.execute('''
            CREATE TABLE IF NOT EXISTS support_tickets (
                id SERIAL PRIMARY KEY,
                ticket_number TEXT UNIQUE NOT NULL,
                user_id BIGINT NOT NULL,
                topic TEXT NOT NULL,
                user_message TEXT NOT NULL,
                admin_response TEXT,
                status TEXT DEFAULT 'open',
                admin_id BIGINT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                CONSTRAINT fk_user_ticket
                    FOREIGN KEY(user_id) 
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
        ''')
        
        # Создаем индекс для быстрого поиска
        await db.pool.execute('''
            CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id 
            ON support_tickets(user_id)
        ''')
        
        await db.pool.execute('''
            CREATE INDEX IF NOT EXISTS idx_support_tickets_ticket_number 
            ON support_tickets(ticket_number)
        ''')
        
        print("✅ Table 'support_tickets' created successfully")
        
        # Проверим что таблица создалась
        exists = await db.pool.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'support_tickets'
            )
        """)
        
        if exists:
            print("✅ Table verification: SUCCESS")
        else:
            print("❌ Table verification: FAILED")
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(create_support_tickets_table())