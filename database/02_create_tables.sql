-- ============================================
-- Создание всех таблиц базы данных
-- ============================================

\c telegram_bot;

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10),
    is_bot BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    openai_thread_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- Индексы для users
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Таблица сообщений
CREATE TABLE IF NOT EXISTS messages (
    message_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    thread_id VARCHAR(255)
);

-- Индексы для messages
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- Таблица тикетов поддержки
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id BIGSERIAL PRIMARY KEY,
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    topic VARCHAR(255) NOT NULL,
    user_message TEXT NOT NULL,
    admin_response TEXT,
    status VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    admin_id BIGINT,
    taken_at TIMESTAMP WITH TIME ZONE,
    channel_message_id BIGINT,
    channel_thread_id INTEGER,
    replied_at TIMESTAMP WITH TIME ZONE
);

-- Индексы для support_tickets
CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_ticket_number ON support_tickets(ticket_number);
CREATE INDEX IF NOT EXISTS idx_tickets_admin_id ON support_tickets(admin_id);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON support_tickets(created_at);

-- Таблица администраторов
CREATE TABLE IF NOT EXISTS admins (
    admin_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    added_by_admin_id BIGINT,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Индексы для admins
CREATE INDEX IF NOT EXISTS idx_admins_user_id ON admins(user_id);
CREATE INDEX IF NOT EXISTS idx_admins_is_active ON admins(is_active);

-- Таблица статистики использования токенов
CREATE TABLE IF NOT EXISTS token_usage (
    usage_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для token_usage
CREATE INDEX IF NOT EXISTS idx_token_usage_user_id ON token_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at);

-- Таблица контента для кнопок и тем
CREATE TABLE IF NOT EXISTS bot_content (
    id BIGSERIAL PRIMARY KEY,
    key VARCHAR NOT NULL,
    content_type VARCHAR NOT NULL,
    content_text TEXT NOT NULL,
    category VARCHAR NOT NULL,
    order_index INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    model VARCHAR,
    button_text VARCHAR,
    command VARCHAR
);

-- Индексы для bot_content
CREATE INDEX IF NOT EXISTS idx_bot_content_category ON bot_content(category);
CREATE INDEX IF NOT EXISTS idx_bot_content_key ON bot_content(key);
CREATE INDEX IF NOT EXISTS idx_bot_content_is_active ON bot_content(is_active);

-- Таблица реферальной системы
CREATE TABLE IF NOT EXISTS referrals (
    referral_id BIGSERIAL PRIMARY KEY,
    referrer_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    referred_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(referrer_id, referred_id)
);

-- Индексы для referrals
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON referrals(referred_id);

-- Выдача прав bot_user на все таблицы
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bot_user;

-- Назначение bot_user владельцем всех таблиц
ALTER TABLE users OWNER TO bot_user;
ALTER TABLE messages OWNER TO bot_user;
ALTER TABLE token_usage OWNER TO bot_user;
ALTER TABLE bot_content OWNER TO bot_user;
ALTER TABLE admins OWNER TO bot_user;
ALTER TABLE support_tickets OWNER TO bot_user;
ALTER TABLE referrals OWNER TO bot_user;

\echo '✅ Все таблицы созданы и права назначены'
