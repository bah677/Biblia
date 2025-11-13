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
        
        # Сначала удалим старые записи если они есть
        await db.pool.execute("DELETE FROM bot_content WHERE category = 'support_topics'")
        
        # Добавляем темы поддержки с правильным content_type
        await db.pool.execute('''
            INSERT INTO bot_content (key, content_type, content_text, category, button_text, order_index, is_active, model)
            VALUES 
            ('tech_support', 'prompt', 'Проблемы с работой бота, ошибки, технические вопросы', 'support_topics', '🔧', 1, true, 'gpt-4'),
            ('feature_help', 'prompt', 'Как использовать функции бота, вопросы по функционалу', 'support_topics', '❓', 2, true, 'gpt-4'),
            ('suggestions', 'prompt', 'Предложения по улучшению бота, новые функции', 'support_topics', '💡', 3, true, 'gpt-4'),
            ('other', 'prompt', 'Другие вопросы, не вошедшие в категории', 'support_topics', '📝', 4, true, 'gpt-4')
        ''')
        
        print("✅ Support topics added to bot_content table")
        
        # Проверим что добавилось
        topics = await db.pool.fetch("SELECT * FROM bot_content WHERE category = 'support_topics'")
        print(f"📋 Now we have {len(topics)} support topics")
        for topic in topics:
            print(f"   - {topic['key']}: {topic['button_text']} {topic['content_text'][:50]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(add_support_topics())