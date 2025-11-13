#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.storage.database import Database
from config import config

async def add_support_topics():
    db = Database(config.database_url)
    await db.connect()
    
    try:
        print("📝 Adding support topics to bot_content table...")
        
        # Добавляем темы поддержки в существующую таблицу bot_content
        await db.pool.execute('''
            INSERT INTO bot_content (key, content_type, content_text, category, button_text, order_index, is_active)
            VALUES 
            ('tech_support', 'support_topic', 'Проблемы с работой бота, ошибки, технические вопросы', 'support_topics', '🔧', 1, true),
            ('feature_help', 'support_topic', 'Как использовать функции бота, вопросы по функционалу', 'support_topics', '❓', 2, true),
            ('suggestions', 'support_topic', 'Предложения по улучшению бота, новые функции', 'support_topics', '💡', 3, true),
            ('other', 'support_topic', 'Другие вопросы, не вошедшие в категории', 'support_topics', '📝', 4, true)
            ON CONFLICT (key) DO NOTHING
        ''')
        
        print("✅ Support topics added to bot_content table")
        
        # Проверим что добавилось
        topics = await db.pool.fetch("SELECT * FROM bot_content WHERE category = 'support_topics'")
        print(f"📋 Now we have {len(topics)} support topics")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(add_support_topics())