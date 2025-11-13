#!/usr/bin/env python3
"""
Скрипт для запуска миграций базы данных
"""
import asyncio
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv('/app/admin_bot/.env')

sys.path.insert(0, '/app')

from shared.storage.migrations import migrate_support_tickets
from admin_bot.config import config

async def main():
    print("=" * 50)
    print("  Running Database Migrations")
    print("=" * 50)
    print()
    
    print(f"Database: {config.DB_NAME}")
    print(f"Host: {config.DB_HOST}:{config.DB_PORT}")
    print()
    
    print("Running migration: support_tickets table...")
    success = await migrate_support_tickets(config.database_url)
    
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        sys.exit(1)
    
    print()
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
