import asyncio
import sys
import os

# Добавляем корневую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.storage.user_storage import UserStorage
from config import config

async def check_database():
    storage = UserStorage(config.database_url)
    await storage.initialize()
    
    try:
        print("=" * 50)
        print("🔍 CHECKING DATABASE STATE")
        print("=" * 50)
        
        # 1. Проверяем кнопки для /more
        print("\n📋 1. BUTTONS FOR /more COMMAND:")
        buttons = await storage.get_more_buttons()
        print(f"   Found: {len(buttons)} buttons")
        
        if buttons:
            for i, btn in enumerate(buttons, 1):
                print(f"   {i}. ID: {btn.get('id')}, Text: '{btn.get('button_text')}', Command: '{btn.get('command')}'")
        else:
            print("   ❌ No buttons found!")
        
        # 2. Проверяем темы поддержки для /support
        print("\n📞 2. SUPPORT TOPICS FOR /support COMMAND:")
        topics = await storage.get_support_topics()
        print(f"   Found: {len(topics)} topics")
        
        if topics:
            for i, topic in enumerate(topics, 1):
                print(f"   {i}. ID: {topic.get('id')}, Name: '{topic.get('name')}', Emoji: '{topic.get('emoji')}'")
        else:
            print("   ❌ No support topics found!")
            
        # 3. Проверяем пользователей (чтобы убедиться что БД работает)
        print("\n👥 3. DATABASE CONNECTION TEST:")
        users = await storage.get_all_users()
        print(f"   Total users in DB: {len(users)}")
        print("   ✅ Database connection is working!")
        
        # 4. Проверяем конкретные таблицы через raw SQL
        print("\n🗃️ 4. TABLE STRUCTURE CHECK:")
        try:
            # Проверяем существование таблицы more_buttons
            more_buttons = await storage.db.pool.fetch("SELECT * FROM more_buttons LIMIT 1")
            print("   ✅ Table 'more_buttons' exists")
        except Exception as e:
            print(f"   ❌ Table 'more_buttons' error: {e}")
            
        try:
            # Проверяем существование таблицы support_topics
            support_topics = await storage.db.pool.fetch("SELECT * FROM support_topics LIMIT 1")
            print("   ✅ Table 'support_topics' exists")
        except Exception as e:
            print(f"   ❌ Table 'support_topics' error: {e}")
        
        print("\n" + "=" * 50)
        print("📊 SUMMARY:")
        if len(buttons) > 0 and len(topics) > 0:
            print("✅ Database seems OK - both buttons and topics exist")
        else:
            print("❌ Problem: Missing buttons or topics in database")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await storage.close()

if __name__ == "__main__":
    print("🚀 Starting database check...")
    asyncio.run(check_database())