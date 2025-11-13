#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.storage.database import Database
from config import config

async def check_support_tickets():
    db = Database(config.database_url)
    await db.connect()
    
    try:
        print("🔍 Checking support_tickets table...")
        
        # Проверим существует ли таблица
        exists = await db.pool.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'support_tickets'
            )
        """)
        
        if exists:
            print("✅ Table 'support_tickets' exists")
            
            # Проверим структуру таблицы
            columns = await db.pool.fetch("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'support_tickets' 
                ORDER BY ordinal_position
            """)
            
            print("📋 Table structure:")
            for col in columns:
                print(f"   - {col['column_name']} ({col['data_type']})")
            
            # Проверим можем ли вставить данные
            try:
                result = await db.pool.execute("""
                    INSERT INTO support_tickets 
                    (ticket_number, user_id, topic, user_message, status) 
                    VALUES ($1, $2, $3, $4, $5)
                """, "TEST-12345", 1, "Test Topic", "Test message", "open")
                
                print("✅ Can insert into support_tickets")
                
                # Удалим тестовую запись
                await db.pool.execute("DELETE FROM support_tickets WHERE ticket_number = $1", "TEST-12345")
                
            except Exception as e:
                print(f"❌ Cannot insert into support_tickets: {e}")
                
        else:
            print("❌ Table 'support_tickets' does not exist")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_support_tickets())