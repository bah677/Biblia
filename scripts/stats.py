#!/usr/bin/env python3
import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.user_storage import UserStorage
from config import config

async def show_stats():
    storage = UserStorage(config.database_url)
    
    try:
        await storage.initialize()
        
        print("=" * 60)
        print("🤖 BOT STATISTICS - PostgreSQL")
        print("=" * 60)
        
        # Общая статистика
        stats = await storage.get_bot_stats()
        all_users = await storage.get_all_users()
        active_users_count = await storage.get_active_users_count(30)
        
        print(f"👥 Total users: {stats.get('total_users', 0)}")
        print(f"🎯 Active users (30 days): {active_users_count}")
        print(f"💬 Total messages: {stats.get('total_messages', 0)}")
        print()
        
        # Последние пользователи
        print("📊 Recent users (last 10):")
        print("-" * 60)
        for user in all_users[:10]:
            created = user['created_at'][:19] if user['created_at'] else 'N/A'
            last_active = user['last_activity'][:19] if user['last_activity'] else 'N/A'
            print(f"ID: {user['user_id']} | @{user['username'] or 'N/A'} | {user['first_name']}")
            print(f"   Created: {created} | Last: {last_active}")
            print(f"   Messages: {user['message_count']} | Thread: {user['openai_thread_id'] or 'No thread'}")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await storage.close()

if __name__ == "__main__":
    asyncio.run(show_stats())