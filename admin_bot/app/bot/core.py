import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from typing import Optional, Dict, Set
from asyncio import Queue, Lock
from datetime import datetime

from config import config
from app.openai_client.assistant import OpenAIClient
from app.storage.user_storage import UserStorage
from app.bot.keyboards import create_more_keyboard, create_support_topics_keyboard, create_my_tickets_keyboard

# Создаем отдельные логгеры
logger = logging.getLogger(__name__)
startup_logger = logging.getLogger('startup')

# 🔥 СОСТОЯНИЯ ДЛЯ СОЗДАНИЯ ТИКЕТА
class SupportStates(StatesGroup):
    waiting_for_topic = State()
    waiting_for_message = State()

class TelegramBot:
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_TOKEN)
        self.dp = Dispatcher()
        self.user_storage = UserStorage(config.database_url)
        self.openai_client: Optional[OpenAIClient] = None
        
        # 🔥 СИСТЕМА ОЧЕРЕДИ ДЛЯ КАЖДОГО ПОЛЬЗОВАТЕЛЯ
        self.user_queues: Dict[int, Queue] = {}
        self.user_locks: Dict[int, Lock] = {}
        self.processing_users: Set[int] = set()
        
        self._register_handlers()
        logger.info("✅ TelegramBot initialized")
    
    def _get_user_queue(self, user_id: int) -> Queue:
        """Получает или создает очередь для пользователя"""
        if user_id not in self.user_queues:
            self.user_queues[user_id] = Queue()
            self.user_locks[user_id] = Lock()
        return self.user_queues[user_id]
    
    def _get_user_lock(self, user_id: int) -> Lock:
        """Получает или создает lock для пользователя"""
        if user_id not in self.user_locks:
            self.user_queues[user_id] = Queue()
            self.user_locks[user_id] = Lock()
        return self.user_locks[user_id]
    
    async def _process_user_messages(self, user_id: int):
        """Обрабатывает сообщения пользователя в порядке FIFO"""
        queue = self._get_user_queue(user_id)
        lock = self._get_user_lock(user_id)
        
        async with lock:
            if user_id in self.processing_users:
                return  # Уже обрабатывается другим процессом
            
            self.processing_users.add(user_id)
        
        try:
            while not queue.empty():
                # 🔥 Берем сообщение из очереди (FIFO)
                message_data = await queue.get()
                message = message_data['message']
                user_message = message_data['text']
                
                logger.info(f"🎯 Processing message from user_id={user_id} (queue position: {queue.qsize() + 1})")
                
                await self._process_single_message(message, user_id, user_message)
                queue.task_done()
                
        finally:
            self.processing_users.discard(user_id)
    
    async def _process_single_message(self, message: Message, user_id: int, user_message: str):
        """Обрабатывает одно сообщение пользователя"""
        # Сохраняем пользователя и обновляем активность
        await self.user_storage.save_user_from_message(message)
        await self.user_storage.update_activity(user_id)
        
        # 🔥 ЗАПУСКАЕМ СТАТУС ПЕЧАТИ СРАЗУ
        typing_task = asyncio.create_task(
            self._send_typing_periodically(message.chat.id)
        )
        
        try:
            collected_text = ""
            bot_message = None
            update_interval = 7
            last_update_time = asyncio.get_event_loop().time()
            chunk_counter = 0
            
            # 🔥 ОТПРАВЛЯЕМ ПЕРВОЕ СООБЩЕНИЕ СРАЗУ
            bot_message = await message.reply("⏳ *Формирую ответ...*", parse_mode=ParseMode.MARKDOWN)
            
            # Обрабатываем потоковый ответ
            async for text_chunk in self.openai_client.process_message_streaming(user_id, user_message):
                if not text_chunk:
                    continue
                
                collected_text += text_chunk
                chunk_counter += 1
                current_time = asyncio.get_event_loop().time()
                
                if current_time - last_update_time >= update_interval:
                    try:
                        display_text = f"{collected_text}\n\n⏳ *Формирую ответ...*"
                        await bot_message.edit_text(
                            display_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        chunk_counter = 0
                        last_update_time = current_time
                    except Exception as e:
                        logger.warning(f"⚠️ Edit failed for user_id={user_id}: {e}")
            
            # Финальное обновление
            if bot_message and collected_text:
                try:
                    await bot_message.edit_text(
                        collected_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Final edit failed for user_id={user_id}: {e}")
                    await message.reply(collected_text)
            
            logger.info(f"✅ Stream processing completed for user_id={user_id}")
            
        except Exception as e:
            error_msg = f"❌ Ошибка при обработке сообщения: {str(e)}"
            logger.error(f"{error_msg} for user_id={user_id}")
            
            try:
                fallback_response = await self.openai_client.process_message_fast(user_id, user_message)
                await message.reply(fallback_response, parse_mode=ParseMode.MARKDOWN)
            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed: {fallback_error}")
                await message.reply("⚠️ Произошла ошибка при обработке вашего сообщения. Попробуйте еще раз.")
        
        finally:
            # 🔥 ГАРАНТИРОВАННО ОСТАНАВЛИВАЕМ СТАТУС ПЕЧАТИ
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass

    async def _message_handler(self, message: Message):
        """Обработчик сообщений с системой очереди FIFO"""
        user_id = message.from_user.id
        user_message = message.text
        
        # 🔥 ИСПРАВЛЕНИЕ: проверяем только команды, а не все сообщения с /
        if user_message and user_message.startswith('/'):
            # Если это команда - пропускаем, у нее есть свои обработчики
            return
        
        # Если сообщение пустое или это не текст - пропускаем
        if not user_message or not message.text:
            return
        
        logger.info(f"📨 Message received from user_id={user_id}: {user_message}")
        
        # 🔥 ДОБАВЛЯЕМ СООБЩЕНИЕ В ОЧЕРЕДЬ ПОЛЬЗОВАТЕЛЯ
        queue = self._get_user_queue(user_id)
        await queue.put({
            'message': message,
            'text': user_message
        })
        
        logger.info(f"📥 Message added to queue for user_id={user_id} (queue size: {queue.qsize()})")
        
        # 🔥 ЗАПУСКАЕМ ОБРАБОТКУ ОЧЕРЕДИ
        asyncio.create_task(self._process_user_messages(user_id))
    
    async def _more_handler(self, message: Message):
        """Обработчик команды /more - показывает кнопки с темами"""
        user_id = message.from_user.id
        
        try:
            # Получаем кнопки из базы данных
            buttons = await self.user_storage.get_more_buttons()
            
            if not buttons:
                await message.answer(
                    "📝 Пока нет доступных тем для поддержки."
                )
                return
            
            # Создаем клавиатуру с кнопками
            keyboard = create_more_keyboard(buttons)
            
            await message.answer(
                "Это не просто кнопки.\n"
                "Это чувства, которые сложно сформулировать.\n"
                "Если узнаешь своё — нажми.\n"
                "Я расскажу, что говорит об этом состоянии Священное Писание.",
                reply_markup=keyboard
            )
            logger.info(f"📋 More buttons shown to user_id={user_id}, count: {len(buttons)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to show more buttons for user_id={user_id}: {e}")
            await message.answer(
                "⚠️ Произошла ошибка при загрузке тем. Попробуйте позже."
            )

    # 🔥 НОВАЯ АРХИТЕКТУРА: УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК CALLBACK
    async def _universal_callback_handler(self, callback: CallbackQuery, state: FSMContext):
        """Универсальный обработчик ВСЕХ callback'ов"""
        user_id = callback.from_user.id
        callback_data = callback.data
        
        logger.info(f"🔔 Universal callback: {callback_data} from user_id={user_id}")
        
        # 🎯 МАРШРУТИЗАЦИЯ ПО ПРЕФИКСАМ
        if callback_data.startswith('more_button_'):
            await self._handle_more_button(callback, state)
        elif callback_data.startswith('support_topic_'):
            await self._handle_support_topic(callback, state)
        elif callback_data == 'support_new':
            await self._handle_support_new(callback, state)
        elif callback_data == 'mytickets_refresh':
            await self._handle_mytickets_refresh(callback, state)
        else:
            logger.warning(f"⚠️ Unknown callback: {callback_data}")
            await callback.answer("❌ Неизвестная команда")

    async def _handle_more_button(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик кнопок из /more"""
        user_id = callback.from_user.id
        
        try:
            # 🔥 ВЫСШИЙ ПРИОРИТЕТ: прерываем любой процесс ТП
            current_state = await state.get_state()
            if current_state and current_state.startswith('SupportStates:'):
                logger.info(f"🎯 Interrupting support process for user {user_id}, starting higher priority task")
                await state.clear()  # Очищаем состояние поддержки
            
            # УДАЛЯЕМ сообщение с кнопками
            await callback.message.delete()
            
            button_id = int(callback.data.replace('more_button_', ''))
            button_info = await self.user_storage.get_button_by_id(button_id)
            
            if not button_info:
                await callback.answer("❌ Тема не найдена")
                return
            
            await callback.answer(f"⏳ Загружаю: {button_info['button_text']}")
            
            # Запускаем статус печати
            typing_task = asyncio.create_task(
                self._send_typing_periodically(callback.message.chat.id)
            )
            
            # Отправляем индикатор обработки как НОВОЕ сообщение
            processing_msg = await callback.message.answer("⏳ Формирую ответ...")
            
            collected_text = ""
            update_interval = 5
            last_update_time = asyncio.get_event_loop().time()
            
            prompt = button_info['content_text']
            await self.user_storage.log_message(user_id, f"Button: {button_info['button_text']}", "user")
            
            # Обрабатываем потоковый ответ
            async for text_chunk in self.openai_client.process_message_streaming(user_id, prompt):
                if not text_chunk:
                    continue
                
                collected_text += text_chunk
                current_time = asyncio.get_event_loop().time()
                
                if current_time - last_update_time >= update_interval:
                    try:
                        await processing_msg.edit_text(
                            f"{collected_text}\n\n🔄 Формирую текст...",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        last_update_time = current_time
                    except Exception as e:
                        logger.warning(f"⚠️ Edit failed for button {button_info['button_text']}: {e}")
            
            # Финальное сообщение
            if collected_text:
                try:
                    await processing_msg.edit_text(collected_text, parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    logger.warning(f"⚠️ Final edit failed: {e}")
                    await callback.message.answer(collected_text, parse_mode=ParseMode.MARKDOWN)
            
            logger.info(f"✅ Button processed: {button_info['button_text']} for user_id={user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process more button for user_id={user_id}: {e}")
            await callback.answer("❌ Ошибка при обработке запроса")
        
        finally:
            # Гарантированно останавливаем статус печати
            if 'typing_task' in locals():
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass

    async def _handle_support_topic(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик выбора темы поддержки"""
        user_id = callback.from_user.id
        
        try:
            topic_id = int(callback.data.replace('support_topic_', ''))
            logger.info(f"🎯 Topic selected: {topic_id} from user_id={user_id}")
            
            # Получаем все темы чтобы найти выбранную
            topics = await self.user_storage.get_support_topics()
            selected_topic = None
            for topic in topics:
                if topic['id'] == topic_id:
                    selected_topic = topic
                    break
            
            if not selected_topic:
                logger.error(f"❌ Topic not found: {topic_id}")
                await callback.answer("❌ Тема не найдена")
                return
            
            # Сохраняем выбранную тему в состоянии
            await state.update_data(selected_topic=selected_topic)
            
            # Переходим к ожиданию сообщения
            await state.set_state(SupportStates.waiting_for_message)
            
            await callback.message.edit_text(
                f"📝 **Тема:** {selected_topic['emoji']} {selected_topic['button_text']}\n\n"
                f"💬 **Опишите вашу проблему подробно:**\n"
                f"• Что произошло?\n"
                f"• Какие действия привели к проблеме?\n"
                f"• Какой результат ожидали?\n\n"
                f"Чем подробнее опишете - тем быстрее поможем! 🛠️",
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"📝 Topic selected: {selected_topic['button_text']} for user_id={user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process support topic for user_id={user_id}: {e}")
            await callback.answer("❌ Ошибка при выборе темы")

    async def _handle_support_new(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик создания нового обращения"""
        user_id = callback.from_user.id
        
        try:
            await state.set_state(SupportStates.waiting_for_topic)
            topics = await self.user_storage.get_support_topics()
            keyboard = create_support_topics_keyboard(topics)
            
            await callback.message.edit_text(
                "📞 **Создание нового обращения**\n\n"
                "Выберите тему:",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"📞 New support ticket started for user_id={user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create new support for user_id={user_id}: {e}")
            await callback.answer("❌ Ошибка при создании обращения")

    async def _handle_mytickets_refresh(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик обновления списка тикетов"""
        user_id = callback.from_user.id
        
        try:
            await self._show_my_tickets(callback.message, user_id)
            await callback.answer("✅ Список обновлен")
            logger.info(f"🔄 Tickets list refreshed for user_id={user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh tickets for user_id={user_id}: {e}")
            await callback.answer("❌ Ошибка при обновлении")

    # 🔥 ТИКЕТ-СИСТЕМА
    
    async def _support_handler(self, message: Message, state: FSMContext):
        """Обработчик команды /support - начинает создание тикета"""
        user_id = message.from_user.id
        
        try:
            logger.info(f"🔄 Support command started for user_id={user_id}")
            
            # Получаем темы поддержки из базы
            topics = await self.user_storage.get_support_topics()
            logger.info(f"📋 Retrieved {len(topics)} support topics from database")
            
            if not topics:
                logger.warning("❌ No support topics found in database")
                await message.answer(
                    "❌ Сервис поддержки временно недоступен. Попробуйте позже."
                )
                return
            
            # Создаем клавиатуру с темами
            keyboard = create_support_topics_keyboard(topics)
            logger.info("✅ Support keyboard created successfully")
            
            await message.answer(
                "📞 **Служба поддержки**\n\n"
                "Выберите тему обращения:\n\n"
                "После выбора темы опишите вашу проблему максимально подробно.",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Устанавливаем состояние ожидания выбора темы
            await state.set_state(SupportStates.waiting_for_topic)
            logger.info(f"✅ Support state set for user_id={user_id}")
            
        except Exception as e:
            logger.error(f"❌ Critical error in support handler for user_id={user_id}: {str(e)}", exc_info=True)
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    async def _support_message_handler(self, message: Message, state: FSMContext):
        """Обработчик сообщения с описанием проблемы"""
        user_id = message.from_user.id
        problem_description = message.text
        
        logger.info(f"🎯 SUPPORT MESSAGE HANDLER CALLED for user_id={user_id}")
        
        try:
            # Получаем сохраненные данные из состояния
            data = await state.get_data()
            selected_topic = data.get('selected_topic')
            
            logger.info(f"📋 Retrieved topic data from state: {selected_topic}")
            
            if not selected_topic:
                await message.answer("❌ Ошибка: тема не выбрана. Начните заново с /support")
                await state.clear()
                return
            
            # Создаем тикет в базе
            ticket_topic = f"{selected_topic['emoji']} {selected_topic['button_text']}"
            ticket_number = await self.user_storage.create_support_ticket(
                user_id, 
                ticket_topic, 
                problem_description
            )
            
            if not ticket_number:
                await message.answer("❌ Не удалось создать обращение. Попробуйте позже.")
                await state.clear()
                return
            
            # Форматируем дату создания
            created_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            
            # Отправляем подтверждение пользователю
            success_message = (
                "✅ **Обращение создано!**\n\n"
                f"🎫 **Тикет:** `{ticket_number}`\n"
                f"📋 **Тема:** {ticket_topic}\n"
                f"💬 **Ваше сообщение:** {problem_description[:100]}...\n"
                f"📊 **Статус:** 🔴 Открыт\n"
                f"⏰ **Создан:** {created_time}\n\n"
                f"Мы ответим в течение **24 часов**.\n"
                f"Для проверки статуса используйте /mytickets"
            )
            
            await message.answer(success_message, parse_mode=ParseMode.MARKDOWN)
            
            # Очищаем состояние
            await state.clear()
            
            logger.info(f"✅ Support ticket created: {ticket_number} for user_id={user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create support ticket for user_id={user_id}: {e}")
            await message.answer("❌ Произошла ошибка при создании обращения. Попробуйте позже.")
            await state.clear()

    async def _mytickets_handler(self, message: Message):
        """Обработчик команды /mytickets - показывает тикеты пользователя"""
        user_id = message.from_user.id
        await self._show_my_tickets(message, user_id)

    async def _show_my_tickets(self, message: Message, user_id: int):
        """Показывает тикеты пользователя"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            tickets = await self.user_storage.get_user_tickets(user_id, limit=5)
            
            if not tickets:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📞 Создать обращение", callback_data="support_new")]
                ])
                
                await message.answer(
                    "📭 **У вас пока нет обращений в поддержку**\n\n"
                    "Хотите создать новое обращение?",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Формируем сообщение со списком тикетов
            tickets_text = "📋 **Ваши обращения в поддержку:**\n\n"
            
            for i, ticket in enumerate(tickets, 1):
                # Статус с эмодзи
                status_emoji = {
                    'open': '🔴',
                    'in_progress': '🟡', 
                    'resolved': '🟢',
                    'closed': '⚫'
                }.get(ticket['status'], '⚪')
                
                # Форматируем дату
                created_date = ticket['created_at'].strftime("%d.%m.%Y")
                
                tickets_text += (
                    f"{i}. **{ticket['ticket_number']}** {status_emoji}\n"
                    f"   📝 {ticket['topic']}\n"
                    f"   🕒 {created_date}\n"
                )
                
                if ticket['admin_response']:
                    tickets_text += f"   💬 Ответ: {ticket['admin_response'][:50]}...\n"
                
                tickets_text += "\n"
            
            tickets_text += "\nДля создания нового обращения используйте /support"
            
            keyboard = create_my_tickets_keyboard()
            await message.answer(tickets_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
            
            logger.info(f"📋 My tickets shown for user_id={user_id}, count: {len(tickets)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to show tickets for user_id={user_id}: {e}")
            await message.answer("❌ Произошла ошибка при загрузке обращений. Попробуйте позже.")
    
    async def _affiliate_handler(self, message: Message):
        """Обработчик команды /affiliate - реферальная система"""
        user_id = message.from_user.id
        
        # 🔥 ГЕНЕРИРУЕМ РЕФЕРАЛЬНУЮ ССЫЛКУ
        bot_username = (await self.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        affiliate_text = (
            "🤝 **Поделись ссылкой с друзьями**\n\n"
            f"[{referral_link}]({referral_link})\n\n"
        )
        
        await message.answer(affiliate_text, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"🔗 Affiliate link generated for user_id={user_id}")
   
    async def _start_handler(self, message: Message):
        """Обработчик команды /start"""
        user = message.from_user
        user_info = f"id={user.id}, username={user.username}, first_name={user.first_name}"
        
        logger.info(f"🎯 Start command from {user_info}")
        startup_logger.info(f"👤 USER STARTED BOT: {user_info}")
        
        # Сохраняем пользователя в базу
        await self.user_storage.save_user_from_message(message)
        
        # 🔥 ПРОВЕРЯЕМ РЕФЕРАЛЬНУЮ ССЫЛКУ (исправленная версия)
        args = None
        if message.text and len(message.text.split()) > 1:
            args = message.text.split()[1]  # Берем аргументы после /start
        
        referrer_id = None
        
        if args and args.startswith('ref_'):
            try:
                referrer_id = int(args[4:])  # Извлекаем ID из "ref_123456"
                
                # Проверяем существует ли реферер
                referrer_data = await self.user_storage.get_user_stats(referrer_id)
                if referrer_data:
                    # Добавляем реферальную связь
                    success = await self.user_storage.add_referral(referrer_id, user.id, args)
                    if success:
                        logger.info(f"✅ Referral added: {user.id} -> {referrer_id}")
                        
                        # Уведомляем реферера
                        try:
                            await self.bot.send_message(
                                referrer_id,
                                f"<b>✨ Твоя ссылка — стала мостом к Свету.</b>\n\n<b>{user.first_name or 'Пользователь'}</b> только что зашёл в бота по твоей рекомендации.\n\nИ, возможно, именно сегодня он получил то слово, которое поддержало, исцелило, дало направление или просто согрело сердце.\n\n📖\n<blockquote>«Блаженны миротворцы, ибо они будут наречены сынами Божиими»\n(Матфея 5:9)</blockquote>",
                                parse_mode=ParseMode.HTML
                            )
                            logger.info(f"✅ Referral notification sent to {referrer_id}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send referral notification to {referrer_id}: {e}")
            except (ValueError, IndexError) as e:
                logger.warning(f"⚠️ Invalid referral args: {args}, error: {e}")
        
        # Получаем или создаем тред для пользователя
        try:
            thread_id = await self.openai_client.get_or_create_thread(user.id)
            
            # Приветственное сообщение
            welcome_msg = (
                "Привет 👋\n"
                "Бог любит тебя и я тоже!\n\n"
                "Я не буду учить тебя жить и раздавать советы, со мной все просто и по-человечески комфортно 🤝\n\n"
                "💬 Здесь тебе не нужно подбирать правильные слова. Просто напиши, что с тобой сейчас происходит, что беспокоит, своими словами, как есть…\n\n"
                "📖 Я подберу слова из Священного Писания и помогу увидеть, как через них Бог отвечает именно в твою ситуацию.🙏\n\n"
                "👉 Также можешь воспользоваться готовыми кнопками запросов в меню, там я собрал самые частые вопросы\n\n📖\n"
                "<blockquote>Мф. 11:28\n«Придите ко Мне все труждающиеся и обременённые, и Я успокою вас».</blockquote>"
            )
            
            # 🔥 ВАЖНО: меняем на HTML для поддержки blockquote
            await message.answer(welcome_msg, parse_mode=ParseMode.HTML)
            logger.info(f"✅ Thread ready for user_id={user.id}: {thread_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup thread for user {user_info}: {e}")
            await message.answer(
                "⚠️ Произошла ошибка при запуске. Попробуйте позже."
            )

    async def initialize(self):
        """Инициализирует зависимости бота"""
        try:
            # Инициализируем хранилище
            await self.user_storage.initialize()
            
            # Создаем OpenAI клиент после инициализации хранилища
            self.openai_client = OpenAIClient(self.user_storage)
            
            logger.info("✅ Bot dependencies initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize bot dependencies: {e}")
            raise
    
    async def close(self):
        """Корректно закрывает ресурсы бота"""
        await self.user_storage.close()
        logger.info("✅ Bot resources closed")
    
    async def delete_webhook(self):
        """Удаляем вебхук перед запуском поллинга"""
        await self.bot.delete_webhook(drop_pending_updates=True)

    def _register_handlers(self):
        """Регистрируем обработчики сообщений"""
        # Команды
        self.dp.message.register(self._start_handler, Command(commands=["start"]))
        self.dp.message.register(self._more_handler, Command(commands=["more"]))
        self.dp.message.register(self._affiliate_handler, Command(commands=["affiliate"]))
        self.dp.message.register(self._support_handler, Command(commands=["support"]))
        self.dp.message.register(self._mytickets_handler, Command(commands=["mytickets"]))
        
        # 🔥 ВАЖНО: Сначала обработчики состояний, потом обычные сообщения
        self.dp.message.register(self._support_message_handler, StateFilter(SupportStates.waiting_for_message))
        self.dp.message.register(self._message_handler)  # Обычные сообщения - ПОСЛЕДНИМ
        
        # 🔥 УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК CALLBACK
        self.dp.callback_query.register(self._universal_callback_handler)
        
        logger.info("✅ All handlers registered including universal callback handler")

    async def _send_typing_periodically(self, chat_id: int):
        """Периодически отправляет статус 'печатает...' в чат"""
        try:
            while True:
                await self.bot.send_chat_action(chat_id, action="typing")
                await asyncio.sleep(4.5)  # 🔥 Уменьшил интервал для более плавного отображения
        except asyncio.CancelledError:
            # 🔥 ПРИ ОТМЕНЕ СРАЗУ ВЫХОДИМ
            return
        except Exception as e:
            logger.error(f"❌ Failed to send typing action: {e}")   
    
    async def start(self):
        """Запуск бота с исправлением проблемы кнопок"""
        logger.info("🔄 Starting bot polling with allowed_updates fix...")
        
        try:
            # Важно: сбрасываем вебхук и настройки
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook reset successfully")
            
            # Даем время на обработку
            await asyncio.sleep(2)
            
            # Явно указываем нужные типы обновлений
            allowed_updates = ["message", "callback_query", "my_chat_member"]
            
            await self.dp.start_polling(
                self.bot,
                allowed_updates=allowed_updates,
                skip_updates=True,
                timeout=60
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
            raise