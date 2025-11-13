#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.storage.database import Database
from config import config

async def check_tables():
    db = Database(config.database_url)
    await db.connect()
    
    try:
        print("=" * 60)
        print("🔍 CHECKING DATABASE STRUCTURE")
        print("=" * 60)
        
        # 1. Получаем список всех таблиц
        print("\n📊 1. ALL TABLES IN DATABASE:")
        tables = await db.pool.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        for i, table in enumerate(tables, 1):
            print(f"   {i}. {table['table_name']}")
        
        # 2. Проверяем структуру каждой таблицы
        print("\n🗃️ 2. TABLE STRUCTURES:")
        for table in tables:
            table_name = table['table_name']
            print(f"\n   📋 Table: {table_name}")
            
            # Получаем колонки таблицы
            columns = await db.pool.fetch("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = $1 
                ORDER BY ordinal_position
            """, table_name)
            
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f"DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"      - {col['column_name']} ({col['data_type']}) {nullable} {default}")
            
            # Проверяем есть ли данные в таблице
            count = await db.pool.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"      📊 Records: {count}")
        
        # 3. Проверяем конкретно таблицы для бота
        print("\n" + "=" * 60)
        print("🤖 BOT-SPECIFIC TABLES CHECK")
        print("=" * 60)
        
        bot_tables = ['more_buttons', 'support_topics', 'support_tickets', 'bot_content']
        for table_name in bot_tables:
            exists = await db.pool.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                )
            """, table_name)
            
            if exists:
                print(f"✅ Table '{table_name}' EXISTS")
                # Покажем несколько записей если есть
                try:
                    records = await db.pool.fetch(f"SELECT * FROM {table_name} LIMIT 3")
                    print(f"   Sample data: {len(records)} records")
                    for record in records:
                        print(f"   - {dict(record)}")
                except Exception as e:
                    print(f"   ❌ Error reading data: {e}")
            else:
                print(f"❌ Table '{table_name}' DOES NOT EXIST")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    print("🚀 Starting database structure check...")
    asyncio.run(check_tables())