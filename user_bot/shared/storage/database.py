import asyncpg
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Создает пул подключений к базе данных"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            await self._init_database()
            logger.info("✅ PostgreSQL connection pool created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise
    
    async def close(self):
        """Закрывает пул подключений"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ PostgreSQL connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Контекстный менеджер для получения подключения"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def _init_database(self):
        """Инициализация таблиц в базе данных"""
        try:
            async with self.get_connection() as conn:
                # Таблица пользователей
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        language_code TEXT,
                        is_premium BOOLEAN DEFAULT FALSE,
                        openai_thread_id TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        message_count INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                # Индексы для ускорения запросов
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC)
                ''')
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity DESC)
                ''')
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_openai_thread ON users(openai_thread_id)
                ''')
                
                # Таблица сообщений для детального лога
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        message_text TEXT,
                        message_type TEXT CHECK (message_type IN ('user', 'assistant')),
                        openai_thread_id TEXT,
                        openai_message_id TEXT,
                        tokens_used INTEGER DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        CONSTRAINT fk_user
                            FOREIGN KEY(user_id) 
                            REFERENCES users(user_id)
                            ON DELETE CASCADE
                    )
                ''')
                
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)
                ''')
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC)
                ''')
                
                # Таблица активности OpenAI
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS openai_activity (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        thread_id TEXT,
                        run_id TEXT,
                        status TEXT,
                        error_message TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        CONSTRAINT fk_user_activity
                            FOREIGN KEY(user_id) 
                            REFERENCES users(user_id)
                            ON DELETE CASCADE
                    )
                ''')
                
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_openai_activity_user_id ON openai_activity(user_id)
                ''')
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_openai_activity_created_at ON openai_activity(created_at DESC)
                ''')
                
                # Таблица для админов
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS admins (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        added_by BIGINT NOT NULL,
                        added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_admins_added_at ON admins(added_at DESC)
                ''')
                
                # Таблица для учета токенов
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS token_usage (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        thread_id TEXT,
                        message_id TEXT,
                        model TEXT NOT NULL,
                        prompt_tokens INTEGER DEFAULT 0,
                        completion_tokens INTEGER DEFAULT 0,
                        total_tokens INTEGER DEFAULT 0,
                        created_date DATE DEFAULT CURRENT_DATE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        CONSTRAINT fk_user_tokens
                            FOREIGN KEY(user_id) 
                            REFERENCES users(user_id)
                            ON DELETE CASCADE
                    )
                ''')
                
                # Индексы для быстрых запросов
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_token_usage_user_date 
                    ON token_usage(user_id, created_date DESC)
                ''')
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_token_usage_date 
                    ON token_usage(created_date DESC)
                ''')
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_token_usage_model 
                    ON token_usage(model)
                ''')
                
            logger.info("✅ PostgreSQL tables initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize database tables: {e}")
            raise
    
    async def add_or_update_user(self, user_data: Dict[str, Any]) -> bool:
        """Добавляет или обновляет пользователя"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, language_code, is_premium, last_activity)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        language_code = EXCLUDED.language_code,
                        is_premium = EXCLUDED.is_premium,
                        last_activity = EXCLUDED.last_activity,
                        message_count = users.message_count + 1,
                        is_active = TRUE
                ''', 
                user_data['user_id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('language_code'),
                user_data.get('is_premium', False),
                datetime.now()
                )
                
                logger.info(f"✅ User saved/updated: user_id={user_data['user_id']}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to save user {user_data['user_id']}: {e}")
            return False
    
    async def update_openai_thread(self, user_id: int, thread_id: str) -> bool:
        """Обновляет thread_id для пользователя"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    'UPDATE users SET openai_thread_id = $1 WHERE user_id = $2',
                    thread_id, user_id
                )
                logger.info(f"✅ Thread updated for user_id={user_id}: {thread_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to update thread for user_id={user_id}: {e}")
            return False
    
    async def update_user_activity(self, user_id: int) -> bool:
        """Обновляет время последней активности"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    'UPDATE users SET last_activity = $1, message_count = message_count + 1 WHERE user_id = $2',
                    datetime.now(), user_id
                )
                return True
        except Exception as e:
            logger.error(f"❌ Failed to update activity for user_id={user_id}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает данные пользователя"""
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM users WHERE user_id = $1', 
                    user_id
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Failed to get user {user_id}: {e}")
            return None
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получает всех пользователей"""
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch(
                    'SELECT * FROM users ORDER BY created_at DESC'
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Failed to get users: {e}")
            return []
    
    async def get_active_users(self, days: int = 30) -> List[Dict[str, Any]]:
        """Получает активных пользователей за последние N дней"""
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM users 
                    WHERE last_activity >= NOW() - INTERVAL '$1 days'
                    ORDER BY last_activity DESC
                ''', days)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Failed to get active users: {e}")
            return []
    
    async def add_message(self, user_id: int, message_text: str, message_type: str, 
                         openai_thread_id: Optional[str] = None, 
                         openai_message_id: Optional[str] = None,
                         tokens_used: int = 0) -> bool:
        """Добавляет сообщение в лог"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT INTO messages 
                    (user_id, message_text, message_type, openai_thread_id, openai_message_id, tokens_used)
                    VALUES ($1, $2, $3, $4, $5, $6)
                ''', 
                user_id,
                message_text,
                message_type,
                openai_thread_id,
                openai_message_id,
                tokens_used
                )
                return True
        except Exception as e:
            logger.error(f"❌ Failed to add message: {e}")
            return False
    
    async def add_openai_activity(self, user_id: int, thread_id: str, run_id: str, 
                                 status: str, error_message: Optional[str] = None) -> bool:
        """Добавляет запись активности OpenAI"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT INTO openai_activity 
                    (user_id, thread_id, run_id, status, error_message)
                    VALUES ($1, $2, $3, $4, $5)
                ''', 
                user_id,
                thread_id,
                run_id,
                status,
                error_message
                )
                return True
        except Exception as e:
            logger.error(f"❌ Failed to add OpenAI activity: {e}")
            return False
    
    async def add_admin(self, user_id: int, username: str, first_name: str, added_by: int) -> bool:
        """Добавляет пользователя в список админов"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT INTO admins (user_id, username, first_name, added_by)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        is_active = TRUE
                ''', user_id, username, first_name, added_by)
                
                logger.info(f"✅ Admin added: user_id={user_id} by added_by={added_by}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to add admin {user_id}: {e}")
            return False

    async def remove_admin(self, user_id: int) -> bool:
        """Удаляет пользователя из списка админов"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    'DELETE FROM admins WHERE user_id = $1',
                    user_id
                )
                logger.info(f"✅ Admin removed: user_id={user_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to remove admin {user_id}: {e}")
            return False

    async def is_admin(self, user_id: int) -> bool:
        """Проверяет является ли пользователь админом"""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval(
                    'SELECT 1 FROM admins WHERE user_id = $1 AND is_active = TRUE',
                    user_id
                )
                return result is not None
        except Exception as e:
            logger.error(f"❌ Failed to check admin status for {user_id}: {e}")
            return False

    async def get_all_admins(self) -> List[Dict[str, Any]]:
        """Получает список всех админов"""
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch('''
                    SELECT a.*, u.username as added_by_username 
                    FROM admins a 
                    LEFT JOIN users u ON a.added_by = u.user_id 
                    WHERE a.is_active = TRUE 
                    ORDER BY a.added_at DESC
                ''')
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Failed to get admins list: {e}")
            return []
    
    async def add_token_usage(self, user_id: int, thread_id: Optional[str], message_id: Optional[str], 
                             model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> bool:
        """Добавляет запись о использовании токенов"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT INTO token_usage 
                    (user_id, thread_id, message_id, model, prompt_tokens, completion_tokens, total_tokens)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''', 
                user_id,
                thread_id,
                message_id,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens
                )
                return True
        except Exception as e:
            logger.error(f"❌ Failed to add token usage: {e}")
            return False

    async def get_user_token_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Получает статистику токенов для пользователя"""
        try:
            async with self.get_connection() as conn:
                # Общая статистика за период
                total_stats = await conn.fetchrow('''
                    SELECT 
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        COUNT(*) as request_count
                    FROM token_usage 
                    WHERE user_id = $1 AND created_date >= CURRENT_DATE - INTERVAL '$2 days'
                ''', user_id, days)
                
                # Статистика по дням
                daily_stats = await conn.fetch('''
                    SELECT 
                        created_date,
                        SUM(prompt_tokens) as prompt_tokens,
                        SUM(completion_tokens) as completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        COUNT(*) as request_count
                    FROM token_usage 
                    WHERE user_id = $1 AND created_date >= CURRENT_DATE - INTERVAL '$2 days'
                    GROUP BY created_date 
                    ORDER BY created_date DESC
                ''', user_id, days)
                
                # Статистика по моделям
                model_stats = await conn.fetch('''
                    SELECT 
                        model,
                        SUM(prompt_tokens) as prompt_tokens,
                        SUM(completion_tokens) as completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        COUNT(*) as request_count
                    FROM token_usage 
                    WHERE user_id = $1 AND created_date >= CURRENT_DATE - INTERVAL '$2 days'
                    GROUP BY model 
                    ORDER BY total_tokens DESC
                ''', user_id, days)
                
                return {
                    'total': dict(total_stats) if total_stats else {},
                    'daily': [dict(row) for row in daily_stats],
                    'models': [dict(row) for row in model_stats]
                }
        except Exception as e:
            logger.error(f"❌ Failed to get user token stats: {e}")
            return {}

    async def get_global_token_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получает глобальную статистику токенов"""
        try:
            async with self.get_connection() as conn:
                # Общая статистика
                total_stats = await conn.fetchrow('''
                    SELECT 
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(*) as total_requests
                    FROM token_usage 
                    WHERE created_date >= CURRENT_DATE - INTERVAL '$1 days'
                ''', days)
                
                # Топ пользователей по токенам
                top_users = await conn.fetch('''
                    SELECT 
                        u.user_id,
                        u.username,
                        u.first_name,
                        SUM(t.total_tokens) as total_tokens,
                        COUNT(t.id) as request_count
                    FROM token_usage t
                    JOIN users u ON t.user_id = u.user_id
                    WHERE t.created_date >= CURRENT_DATE - INTERVAL '$1 days'
                    GROUP BY u.user_id, u.username, u.first_name
                    ORDER BY total_tokens DESC
                    LIMIT 10
                ''', days)
                
                # Статистика по дням
                daily_stats = await conn.fetch('''
                    SELECT 
                        created_date,
                        SUM(prompt_tokens) as prompt_tokens,
                        SUM(completion_tokens) as completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(*) as request_count
                    FROM token_usage 
                    WHERE created_date >= CURRENT_DATE - INTERVAL '$1 days'
                    GROUP BY created_date 
                    ORDER BY created_date DESC
                ''', days)
                
                return {
                    'total': dict(total_stats) if total_stats else {},
                    'top_users': [dict(row) for row in top_users],
                    'daily': [dict(row) for row in daily_stats]
                }
        except Exception as e:
            logger.error(f"❌ Failed to get global token stats: {e}")
            return {}
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Получает общую статистику пользователей"""
        try:
            async with self.get_connection() as conn:
                total_users = await conn.fetchval('SELECT COUNT(*) FROM users')
                active_users = await conn.fetchval('''
                    SELECT COUNT(*) FROM users 
                    WHERE last_activity >= NOW() - INTERVAL '30 days'
                ''')
                total_messages = await conn.fetchval('SELECT COUNT(*) FROM messages')
                
                return {
                    'total_users': total_users,
                    'active_users_30d': active_users,
                    'total_messages': total_messages
                }
        except Exception as e:
            logger.error(f"❌ Failed to get user stats: {e}")
            return {}