#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.storage.database import Database
from config import config

async def check_content_types():
    db = Database(config.database_url)
    await db.connect()
    
    try:
        print("🔍 Checking allowed content types...")
        
        # Проверим существующие значения content_type
        content_types = await db.pool.fetch("""
            SELECT DISTINCT content_type, COUNT(*) 
            FROM bot_content 
            GROUP BY content_type 
            ORDER BY content_type
        """)
        
        print("📋 Existing content types:")
        for row in content_types:
            print(f"   - '{row['content_type']}': {row['count']} records")
        
        # Проверим check constraint
        constraints = await db.pool.fetch("""
            SELECT conname, pg_get_constraintdef(oid) 
            FROM pg_constraint 
            WHERE conrelid = 'bot_content'::regclass AND contype = 'c'
        """)
        
        print("\n🔒 Check constraints:")
        for row in constraints:
            print(f"   - {row['conname']}: {row['pg_get_constraintdef']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_content_types())