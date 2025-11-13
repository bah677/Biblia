import logging
import asyncio
import sys
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from typing import Optional
from datetime import datetime

# Добавляем путь к shared модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from config import config
from shared.storage.user_storage import UserStorage

logger = logging.getLogger(__name__)

# Состояния для работы с тикетами
class TicketStates(StatesGroup):
    waiting_for_reply = State()
    waiting_for_close_reason = State()

class AdminBot:
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_TOKEN)
        self.dp = Dispatcher()
        self.user_storage = UserStorage(config.database_url)
        
        self._register_handlers()
        logger.info("✅ AdminBot initialized")
    
    async def initialize(self):
        """Инициализирует зависимости бота"""
        try:
            await self.user_storage.initialize()
            
            # Запускаем миграции
            from shared.storage.migrations import migrate_support_tickets
            await migrate_support_tickets(config.database_url)
            
            logger.info("✅ Admin bot dependencies initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize admin bot dependencies: {e}")
            raise
    
    async def close(self):
        """Корректно закрывает ресурсы бота"""
        await self.user_storage.close()
        logger.info("✅ Admin bot resources closed")
    
    # ==================== КОМАНДЫ АДМИНА ====================
    
    async def _start_handler(self, message: Message):
        """Обработчик команды /start"""
        user_id = message.from_user.id
        
        # Проверяем права админа
        is_admin = await self.user_storage.is_admin(user_id)
        is_super_admin = await self.user_storage.is_super_admin(user_id)
        
        if not (is_admin or is_super_admin):
            await message.answer("❌ У вас нет прав доступа к этому боту.")
            return
        
        # Проверяем deep link для тикета
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if args and args[0].startswith('ticket_'):
            ticket_number = args[0].replace('ticket_', '')
            await self._show_ticket_details(message, ticket_number)
            return
        
        welcome_msg = (
            "👑 **ПАНЕЛЬ АДМИНИСТРАТОРА**\n\n"
            "📊 **Статистика:**\n"
            "/stats - Общая статистика бота\n"
            "/token_stats - Статистика токенов\n"
            "/token_leaderboard - Топ пользователей по токенам\n\n"
            "🎫 **Тикеты поддержки:**\n"
            "/tickets - Список активных тикетов\n"
            "/my_tickets - Мои взятые тикеты\n\n"
        )
        
        if is_super_admin:
            welcome_msg += (
                "🔐 **Управление админами:**\n"
                "/add_admin <user_id> - Добавить админа\n"
                "/remove_admin <user_id> - Удалить админа\n"
                "/list_admins - Список админов\n"
            )
        
        await message.answer(welcome_msg, parse_mode=ParseMode.MARKDOWN)
    
    async def _show_ticket_details(self, message: Message, ticket_number: str):
        """Показывает детали тикета"""
        try:
            ticket = await self.user_storage.get_ticket_by_number(ticket_number)
            
            if not ticket:
                await message.answer("❌ Тикет не найден")
                return
            
            status_emoji = {
                'open': '🔴',
                'in_progress': '🟡',
                'resolved': '🟢',
                'closed': '⚫'
            }.get(ticket['status'], '⚪')
            
            created_date = ticket['created_at'].strftime("%d.%m.%Y %H:%M")
            
            ticket_text = (
                f"🎫 **Тикет:** `{ticket['ticket_number']}`\n"
                f"{status_emoji} **Статус:** {ticket['status']}\n"
                f"📋 **Тема:** {ticket['topic']}\n"
                f"👤 **User ID:** `{ticket['user_id']}`\n"
                f"⏰ **Создан:** {created_date}\n\n"
                f"💬 **Проблема:**\n{ticket['user_message']}\n"
            )
            
            if ticket['admin_response']:
                ticket_text += f"\n📝 **Ответ админа:**\n{ticket['admin_response']}"
            
            # Кнопки действий
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            buttons = []
            
            if ticket['status'] == 'open':
                buttons.append([InlineKeyboardButton(
                    text="✋ Взять в работу",
                    callback_data=f"take_ticket_{ticket['ticket_number']}"
                )])
            
            if ticket['status'] in ['open', 'in_progress']:
                buttons.append([InlineKeyboardButton(
                    text="💬 Ответить",
                    callback_data=f"reply_ticket_{ticket['ticket_number']}"
                )])
                buttons.append([InlineKeyboardButton(
                    text="✅ Закрыть",
                    callback_data=f"close_ticket_{ticket['ticket_number']}"
                )])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
            
            await message.answer(ticket_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"❌ Error showing ticket details: {e}")
            await message.answer("❌ Ошибка при загрузке тикета")
    
    async def _tickets_handler(self, message: Message):
        """Показывает список активных тикетов"""
        user_id = message.from_user.id
        
        if not await self._check_admin(user_id, message):
            return
        
        try:
            tickets = await self.user_storage.get_all_open_tickets()
            
            if not tickets:
                await message.answer("📭 Нет активных тикетов")
                return
            
            tickets_text = "🎫 **Активные тикеты:**\n\n"
            
            for ticket in tickets[:10]:  # Показываем первые 10
                status_emoji = {
                    'open': '🔴',
                    'in_progress': '🟡'
                }.get(ticket['status'], '⚪')
                
                created_date = ticket['created_at'].strftime("%d.%m %H:%M")
                
                # Добавляем инфо о том кто взял
                admin_info = ""
                if ticket.get('admin_id'):
                    admin_info = f"   👤 Взял: Admin ID {ticket['admin_id']}\n"
                
                tickets_text += (
                    f"{status_emoji} **{ticket['ticket_number']}**\n"
                    f"   📋 {ticket['topic']}\n"
                    f"   🕒 {created_date}\n"
                    f"{admin_info}"
                    f"   /view_{ticket['ticket_number']}\n\n"
                )
            
            await message.answer(tickets_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"❌ Error getting tickets: {e}")
            await message.answer("❌ Ошибка при загрузке тикетов")
    
    async def _my_tickets_handler(self, message: Message):
        """Показывает тикеты, взятые админом"""
        user_id = message.from_user.id
        
        if not await self._check_admin(user_id, message):
            return
        
        try:
            tickets = await self.user_storage.get_admin_tickets(user_id)
            
            if not tickets:
                await message.answer("📭 У вас нет взятых тикетов")
                return
            
            tickets_text = "🎫 **Ваши тикеты:**\n\n"
            
            for ticket in tickets:
                status_emoji = {
                    'in_progress': '🟡',
                    'resolved': '🟢'
                }.get(ticket['status'], '⚪')
                
                tickets_text += (
                    f"{status_emoji} **{ticket['ticket_number']}**\n"
                    f"   📋 {ticket['topic']}\n"
                    f"   /view_{ticket['ticket_number']}\n\n"
                )
            
            await message.answer(tickets_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"❌ Error getting my tickets: {e}")
            await message.answer("❌ Ошибка при загрузке тикетов")
    
    # ==================== CALLBACK HANDLERS ====================
    
    async def _take_ticket_callback(self, callback: CallbackQuery):
        """Обработчик взятия тикета в работу"""
        user_id = callback.from_user.id
        ticket_number = callback.data.replace('take_ticket_', '')
        
        try:
            success = await self.user_storage.assign_ticket_to_admin(ticket_number, user_id)
            
            if not success:
                await callback.answer("❌ Не удалось взять тикет")
                return
            
            # Редактируем сообщение в группе
            ticket = await self.user_storage.get_ticket_by_number(ticket_number)
            if ticket and ticket.get('channel_message_id'):
                await self._update_ticket_in_group(
                    ticket, 
                    f"✋ **В РАБОТЕ У:** {callback.from_user.first_name}"
                )
            
            await callback.message.edit_text(
                f"✅ Вы взяли тикет **{ticket_number}** в работу!\n\n"
                f"Используйте /view_{ticket_number} для просмотра деталей",
                parse_mode=ParseMode.MARKDOWN
            )
            
            await callback.answer("✅ Тикет взят в работу!")
            
        except Exception as e:
            logger.error(f"❌ Error taking ticket: {e}")
            await callback.answer("❌ Ошибка при взятии тикета")
    
    async def _reply_ticket_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик кнопки ответа на тикет"""
        ticket_number = callback.data.replace('reply_ticket_', '')
        
        await state.update_data(ticket_number=ticket_number)
        await state.set_state(TicketStates.waiting_for_reply)
        
        await callback.message.answer(
            f"💬 Напишите ваш ответ на тикет **{ticket_number}**:\n\n"
            f"Ваш ответ будет отправлен пользователю.",
            parse_mode=ParseMode.MARKDOWN
        )
        await callback.answer()
    
    async def _close_ticket_callback(self, callback: CallbackQuery):
        """Обработчик закрытия тикета"""
        user_id = callback.from_user.id
        ticket_number = callback.data.replace('close_ticket_', '')
        
        try:
            success = await self.user_storage.close_ticket(ticket_number, user_id)
            
            if not success:
                await callback.answer("❌ Не удалось закрыть тикет")
                return
            
            await callback.message.edit_text(
                f"✅ Тикет **{ticket_number}** закрыт!",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Удаляем сообщение из группы (тикет закрыт)
            ticket = await self.user_storage.get_ticket_by_number(ticket_number)
            if ticket and ticket.get('channel_message_id'):
                try:
                    await self.bot.delete_message(
                        config.ADMIN_CHANNEL_ID,
                        ticket['channel_message_id']
                    )
                    logger.info(f"✅ Deleted closed ticket message from group")
                except Exception as e:
                    logger.warning(f"Could not delete ticket message: {e}")
            
            await callback.answer("✅ Тикет закрыт!")
            
        except Exception as e:
            logger.error(f"❌ Error closing ticket: {e}")
            await callback.answer("❌ Ошибка при закрытии тикета")
    
    async def _reply_message_handler(self, message: Message, state: FSMContext):
        """Обработчик ответа на тикет"""
        user_id = message.from_user.id
        reply_text = message.text
        
        data = await state.get_data()
        ticket_number = data.get('ticket_number')
        
        if not ticket_number:
            await message.answer("❌ Ошибка: тикет не найден")
            await state.clear()
            return
        
        try:
            success = await self.user_storage.add_admin_reply(
                ticket_number,
                user_id,
                reply_text
            )
            
            if not success:
                await message.answer("❌ Не удалось отправить ответ")
                await state.clear()
                return
            
            # Получаем информацию о тикете и пользователе
            ticket = await self.user_storage.get_ticket_by_number(ticket_number)
            
            if ticket:
                # Отправляем ответ пользователю через user_bot
                # Здесь нужен USER BOT TOKEN для отправки
                # Пока просто логируем
                logger.info(f"Reply to user {ticket['user_id']}: {reply_text}")
            
            await message.answer(
                f"✅ Ответ отправлен на тикет **{ticket_number}**!",
                parse_mode=ParseMode.MARKDOWN
            )
            
            await state.clear()
            
        except Exception as e:
            logger.error(f"❌ Error sending reply: {e}")
            await message.answer("❌ Ошибка при отправке ответа")
            await state.clear()
    
    # ==================== СТАТИСТИКА ====================
    
    async def _stats_handler(self, message: Message):
        """Показывает общую статистику бота"""
        user_id = message.from_user.id
        
        if not await self._check_admin(user_id, message):
            return
        
        try:
            stats = await self.user_storage.get_bot_stats()
            
            stats_text = (
                "📊 **СТАТИСТИКА БОТА**\n\n"
                f"👥 Всего пользователей: **{stats.get('total_users', 0)}**\n"
                f"✅ Активных (30 дней): **{stats.get('active_users_30d', 0)}**\n"
                f"💬 Всего сообщений: **{stats.get('total_messages', 0)}**\n"
            )
            
            await message.answer(stats_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            await message.answer("❌ Ошибка при получении статистики")
    
    async def _token_stats_handler(self, message: Message):
        """Показывает статистику токенов"""
        user_id = message.from_user.id
        
        if not await self._check_admin(user_id, message):
            return
        
        # Парсим количество дней
        args = message.text.split()[1:]
        days = int(args[0]) if args and args[0].isdigit() else 7
        
        try:
            stats = await self.user_storage.get_global_token_stats(days)
            total = stats.get('total', {})
            
            stats_text = (
                f"📊 **СТАТИСТИКА ТОКЕНОВ** (за {days} дней)\n\n"
                f"🔢 Всего токенов: **{total.get('total_tokens', 0):,}**\n"
                f"📤 Prompt: **{total.get('total_prompt_tokens', 0):,}**\n"
                f"📥 Completion: **{total.get('total_completion_tokens', 0):,}**\n"
                f"👥 Уникальных пользователей: **{total.get('unique_users', 0)}**\n"
                f"📨 Всего запросов: **{total.get('total_requests', 0)}**\n"
            )
            
            await message.answer(stats_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"❌ Error getting token stats: {e}")
            await message.answer("❌ Ошибка при получении статистики токенов")
    
    async def _token_leaderboard_handler(self, message: Message):
        """Показывает топ пользователей по токенам"""
        user_id = message.from_user.id
        
        if not await self._check_admin(user_id, message):
            return
        
        args = message.text.split()[1:]
        days = int(args[0]) if args and args[0].isdigit() else 7
        
        try:
            stats = await self.user_storage.get_global_token_stats(days)
            top_users = stats.get('top_users', [])
            
            if not top_users:
                await message.answer("📭 Нет данных за указанный период")
                return
            
            leaderboard_text = f"🏆 **ТОП ПОЛЬЗОВАТЕЛЕЙ** (за {days} дней)\n\n"
            
            for i, user in enumerate(top_users[:10], 1):
                emoji = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}.')
                leaderboard_text += (
                    f"{emoji} **{user.get('first_name', 'Unknown')}** "
                    f"(@{user.get('username', 'no_username')})\n"
                    f"   🔢 {user.get('total_tokens', 0):,} токенов "
                    f"({user.get('request_count', 0)} запросов)\n\n"
                )
            
            await message.answer(leaderboard_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"❌ Error getting leaderboard: {e}")
            await message.answer("❌ Ошибка при получении рейтинга")
    
    # ==================== УПРАВЛЕНИЕ АДМИНАМИ ====================

    async def _view_ticket_handler(self, message: Message):
        """Обработчик команды /viewTKT... для просмотра тикета"""
        user_id = message.from_user.id
        
        if not await self._check_admin(user_id, message):
            return
        
        # Извлекаем номер тикета из команды
        command_text = message.text
        if command_text.startswith('/view'):
            ticket_number = command_text[5:].strip()  # Убираем /view
            if ticket_number:
                await self._show_ticket_details(message, ticket_number)
            else:
                await message.answer("❌ Укажите номер тикета: /viewTKT12345678")
        else:
            await message.answer("❌ Неверный формат команды")
    

    
    async def _add_admin_handler(self, message: Message):
        """Добавляет нового админа"""
        user_id = message.from_user.id
        
        if not await self.user_storage.is_super_admin(user_id):
            await message.answer("❌ Только суперадмин может добавлять админов")
            return
        
        args = message.text.split()[1:]
        
        if not args or not args[0].isdigit():
            await message.answer("❌ Использование: /add_admin <user_id>")
            return
        
        new_admin_id = int(args[0])
        
        try:
            success = await self.user_storage.add_admin(
                new_admin_id,
                f"user_{new_admin_id}",
                f"Admin {new_admin_id}",
                user_id
            )
            
            if success:
                await message.answer(f"✅ Админ `{new_admin_id}` добавлен!", parse_mode=ParseMode.MARKDOWN)
            else:
                await message.answer("❌ Не удалось добавить админа")
                
        except Exception as e:
            logger.error(f"❌ Error adding admin: {e}")
            await message.answer("❌ Ошибка при добавлении админа")
    
    async def _remove_admin_handler(self, message: Message):
        """Удаляет админа"""
        user_id = message.from_user.id
        
        if not await self.user_storage.is_super_admin(user_id):
            await message.answer("❌ Только суперадмин может удалять админов")
            return
        
        args = message.text.split()[1:]
        
        if not args or not args[0].isdigit():
            await message.answer("❌ Использование: /remove_admin <user_id>")
            return
        
        admin_id = int(args[0])
        
        try:
            success = await self.user_storage.remove_admin(admin_id)
            
            if success:
                await message.answer(f"✅ Админ `{admin_id}` удален!", parse_mode=ParseMode.MARKDOWN)
            else:
                await message.answer("❌ Не удалось удалить админа")
                
        except Exception as e:
            logger.error(f"❌ Error removing admin: {e}")
            await message.answer("❌ Ошибка при удалении админа")
    
    async def _list_admins_handler(self, message: Message):
        """Показывает список админов"""
        user_id = message.from_user.id
        
        if not await self._check_admin(user_id, message):
            return
        
        try:
            admins = await self.user_storage.get_all_admins()
            
            if not admins:
                await message.answer("📭 Нет активных админов")
                return
            
            admins_text = "👑 **СПИСОК АДМИНОВ:**\n\n"
            
            for admin in admins:
                admin_id = admin.get('user_id')
                is_super = admin_id == config.SUPER_ADMIN_ID
                
                admins_text += (
                    f"{'👑' if is_super else '👤'} **{admin.get('first_name', 'Unknown')}**\n"
                    f"   ID: `{admin_id}`\n"
                    f"   Username: @{admin.get('username', 'no_username')}\n"
                    f"   Добавлен: {admin.get('added_at', 'N/A')}\n\n"
                )
            
            await message.answer(admins_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"❌ Error getting admins list: {e}")
            await message.answer("❌ Ошибка при получении списка админов")
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    async def _check_admin(self, user_id: int, message: Message) -> bool:
        """Проверяет права админа"""
        is_admin = await self.user_storage.is_admin(user_id)
        is_super_admin = await self.user_storage.is_super_admin(user_id)
        
        if not (is_admin or is_super_admin):
            await message.answer("❌ У вас нет прав доступа")
            return False
        
        return True

    async def _update_ticket_in_group(self, ticket: dict, status_text: str):
        """Редактирует сообщение о тикете в группе"""
        try:
            if not ticket.get('channel_message_id'):
                return
            
            # Формируем обновленное сообщение БЕЗ ССЫЛКИ
            updated_text = (
                f"🎫 **ТИКЕТ:** `{ticket['ticket_number']}`\n"
                f"📋 **Тема:** {ticket['topic']}\n"
                f"👤 **User ID:** `{ticket['user_id']}`\n\n"
                f"{status_text}\n\n"
                f"💬 **Проблема:**\n{ticket.get('user_message', '')[:200]}..."
            )
            
            await self.bot.edit_message_text(
                text=updated_text,
                chat_id=config.ADMIN_CHANNEL_ID,
                message_id=ticket['channel_message_id'],
                parse_mode=ParseMode.MARKDOWN,
                message_thread_id=ticket.get('channel_thread_id')
            )
            
            logger.info(f"✅ Updated ticket {ticket['ticket_number']} message in group")
            
        except Exception as e:
            logger.error(f"❌ Error updating ticket in group: {e}")

    
    async def _send_channel_notification(self, text: str, thread_id: Optional[int] = None):
        """Отправляет уведомление в админский канал"""
        try:
            await self.bot.send_message(
                config.ADMIN_CHANNEL_ID,
                text,
                parse_mode=ParseMode.MARKDOWN,
                message_thread_id=thread_id
            )
        except Exception as e:
            logger.error(f"❌ Error sending channel notification: {e}")
    
    async def post_ticket_to_channel(self, ticket: dict):
        """Постит новый тикет в канал"""
        try:
            bot_username = (await self.bot.get_me()).username
            deep_link = f"https://t.me/{bot_username}?start=ticket_{ticket['ticket_number']}"
            
            created_date = ticket['created_at'].strftime("%d.%m.%Y %H:%M")
            
            ticket_text = (
                f"🆕 **НОВЫЙ ТИКЕТ ПОДДЕРЖКИ**\n\n"
                f"🎫 **Номер:** `{ticket['ticket_number']}`\n"
                f"📋 **Тема:** {ticket['topic']}\n"
                f"👤 **User ID:** `{ticket['user_id']}`\n"
                f"⏰ **Создан:** {created_date}\n\n"
                f"💬 **Проблема:**\n{ticket['message'][:500]}...\n\n"
                f"[🔗 Взять в работу]({deep_link})"
            )
            
            # Постим в канал (пока без топика, потом добавим)
            msg = await self.bot.send_message(
                config.ADMIN_CHANNEL_ID,
                ticket_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Сохраняем ID сообщения в базе
            await self.user_storage.update_ticket_channel_message(
                ticket['ticket_number'],
                msg.message_id,
                None  # thread_id будет позже
            )
            
            logger.info(f"✅ Ticket {ticket['ticket_number']} posted to channel")
            
        except Exception as e:
            logger.error(f"❌ Error posting ticket to channel: {e}")
    
    # ==================== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ====================
    
    def _register_handlers(self):
        """Регистрируем обработчики"""
        # Команды
        self.dp.message.register(self._start_handler, Command(commands=["start"]))
        self.dp.message.register(self._tickets_handler, Command(commands=["tickets"]))
        self.dp.message.register(self._my_tickets_handler, Command(commands=["my_tickets"]))
        self.dp.message.register(self._stats_handler, Command(commands=["stats"]))
        self.dp.message.register(self._token_stats_handler, Command(commands=["token_stats"]))
        self.dp.message.register(self._token_leaderboard_handler, Command(commands=["token_leaderboard"]))
        self.dp.message.register(self._add_admin_handler, Command(commands=["add_admin"]))
        self.dp.message.register(self._remove_admin_handler, Command(commands=["remove_admin"]))
        self.dp.message.register(self._list_admins_handler, Command(commands=["list_admins"]))
        
        # Обработчик для команд /viewTKT...
        self.dp.message.register(
            self._view_ticket_handler,
            lambda msg: msg.text and msg.text.startswith('/view')
        )
        
        # Состояния
        self.dp.message.register(self._reply_message_handler, StateFilter(TicketStates.waiting_for_reply))
        
        # Callback кнопки
        self.dp.callback_query.register(
            self._take_ticket_callback,
            F.data.startswith("take_ticket_")
        )
        self.dp.callback_query.register(
            self._reply_ticket_callback,
            F.data.startswith("reply_ticket_")
        )
        self.dp.callback_query.register(
            self._close_ticket_callback,
            F.data.startswith("close_ticket_")
        )
        
        logger.info("✅ All admin handlers registered")
    
    async def start(self):
        """Запуск админского бота"""
        logger.info("🔄 Starting admin bot polling...")
        
        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook reset successfully")
            
            await asyncio.sleep(1)
            
            allowed_updates = ["message", "callback_query"]
            
            await self.dp.start_polling(
                self.bot,
                allowed_updates=allowed_updates,
                skip_updates=True
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to start admin bot: {e}")
            raise
