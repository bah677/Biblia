# Telegram Bot Project - User & Admin Bots

Проект разделен на два независимых бота:
- **User Bot** - основной бот для пользователей
- **Admin Bot** - админский бот для управления и поддержки

## Структура проекта

```
/app/
├── user_bot/          # Основной бот для пользователей
│   ├── main.py
│   ├── config.py
│   ├── .env
│   └── app/
│       ├── bot/
│       ├── openai_client/
│       └── helpers/
│
├── admin_bot/         # Админский бот
│   ├── main.py
│   ├── config.py
│   ├── .env
│   └── app/
│       └── bot/
│
└── shared/           # Общие компоненты
    ├── storage/      # База данных (общая)
    └── models/       # Модели данных
```

## User Bot (Основной бот)

**Токен:** `7404722403:AAFm8MZDlhLoBMRtYlICDMNXyJ01U7TAdI4`

### Функции:
- `/start` - Приветствие и работа с OpenAI Assistant
- `/more` - Показ кнопок с темами из Писания
- `/support` - Создание тикета поддержки
- `/mytickets` - Просмотр своих тикетов
- `/affiliate` - Реферальная система

### Запуск:
```bash
cd /app/user_bot
python main.py
```

## Admin Bot (Админский бот)

**Токен:** `7763530661:AAFrnrbArarKPG_iCdPvreLZHrXee7ymsyE`
**Канал:** `https://t.me/+WLn4SNrLCjRiMDIy` (ID: `-1002339461988`)

### Функции:

#### Статистика:
- `/stats` - Общая статистика бота
- `/token_stats [дней]` - Статистика токенов
- `/token_leaderboard [дней]` - Топ пользователей по токенам

#### Управление тикетами:
- `/tickets` - Список активных тикетов
- `/my_tickets` - Мои взятые тикеты
- Deep links: `t.me/bot?start=ticket_TKT123` - Просмотр конкретного тикета

#### Управление админами (только суперадмин):
- `/add_admin <user_id>` - Добавить админа
- `/remove_admin <user_id>` - Удалить админа
- `/list_admins` - Список админов

### Запуск:
```bash
cd /app/admin_bot
python main.py
```

## База данных (PostgreSQL)

Общая для обоих ботов:
- **Host:** localhost
- **Port:** 5432
- **Database:** telegram_bot
- **User:** bot_user
- **Password:** eyo3uZh8uWsrinldTe

### Таблицы:
- `users` - Пользователи
- `messages` - Сообщения
- `support_tickets` - Тикеты поддержки
- `admins` - Администраторы
- `token_usage` - Статистика токенов
- `bot_content` - Контент (кнопки, темы)
- `referrals` - Реферальная система

## Workflow тикетов

1. **Пользователь создает тикет** через User Bot (`/support`)
2. **User Bot сохраняет** тикет в базу данных
3. **Admin Bot автоматически постит** тикет в админский канал с deep link
4. **Админ кликает** по ссылке → попадает в Admin Bot
5. **Админ берет тикет** в работу → сообщение удаляется из канала
6. **Админ отвечает** → ответ сохраняется в базе
7. **Админ закрывает** тикет

## Миграции

При первом запуске Admin Bot автоматически добавит новые поля в таблицу `support_tickets`:
- `admin_id` - ID админа, взявшего тикет
- `taken_at` - Время взятия в работу
- `channel_message_id` - ID сообщения в канале
- `channel_thread_id` - ID топика в канале
- `replied_at` - Время ответа админа

## Запуск через Supervisor

Можно запустить оба бота одновременно:

```bash
# Запуск обоих ботов
sudo supervisorctl start user_bot admin_bot

# Проверка статуса
sudo supervisorctl status

# Перезапуск
sudo supervisorctl restart user_bot admin_bot

# Просмотр логов
tail -f /app/user_bot/logs/general.log
tail -f /app/admin_bot/logs/admin_bot.log
```

## Переменные окружения

### User Bot (.env):
```
TELEGRAM_TOKEN=...
OPENAI_API_KEY=...
ASSISTANT_ID=...
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_bot
DB_USER=bot_user
DB_PASSWORD=...
SUPER_ADMIN_ID=304631563
ADMIN_BOT_TOKEN=...
```

### Admin Bot (.env):
```
TELEGRAM_TOKEN=...
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_bot
DB_USER=bot_user
DB_PASSWORD=...
SUPER_ADMIN_ID=304631563
ADMIN_CHANNEL_ID=-1002339461988
ADMIN_CHANNEL_LINK=https://t.me/+WLn4SNrLCjRiMDIy
```

## Суперадмин

**User ID:** `304631563`

Только суперадмин может:
- Добавлять/удалять админов
- Видеть полную статистику
- Управлять ботом

## Разработка

### Установка зависимостей:
```bash
pip install -r requirements.txt
```

### Требования:
- Python 3.10+
- PostgreSQL 12+
- aiogram 3.10+
- openai 1.0+
- asyncpg 0.28+

## Логи

- User Bot: `/app/user_bot/logs/general.log`, `/app/user_bot/logs/startup.log`
- Admin Bot: `/app/admin_bot/logs/admin_bot.log`

## Контакты

Для вопросов и поддержки обращайтесь к разработчику.
