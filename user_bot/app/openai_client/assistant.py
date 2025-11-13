import logging
import asyncio
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI
from app.storage.user_storage import UserStorage

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self, user_storage: UserStorage):
        from config import config
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.assistant_id = config.ASSISTANT_ID
        self.user_storage = user_storage
        logger.info("✅ OpenAIClient initialized")
    
    async def get_or_create_thread(self, user_id: int) -> str:
        """Получает или создает тред для пользователя"""
        try:
            # Проверяем есть ли сохраненный thread_id
            thread_id = await self.user_storage.get_thread_id(user_id)
            
            if thread_id:
                logger.info(f"📖 Existing thread found for user_id={user_id}: {thread_id}")
                return thread_id
            
            # Создаем новый тред
            thread = await self.client.beta.threads.create()
            thread_id = thread.id
            
            # Сохраняем в хранилище
            await self.user_storage.save_thread_id(user_id, thread_id)
            
            # Логируем активность
            await self.user_storage.log_openai_activity(
                user_id, thread_id, "", "thread_created", "New thread created"
            )
            
            logger.info(f"✅ New thread created for user_id={user_id}: {thread_id}")
            return thread_id
            
        except Exception as e:
            logger.error(f"❌ Failed to get/create thread for user_id={user_id}: {e}")
            await self.user_storage.log_openai_activity(
                user_id, "", "", "thread_error", str(e)
            )
            raise
    
    async def process_message_streaming(self, user_id: int, message: str) -> AsyncGenerator[str, None]:
        """Обрабатывает сообщение с streaming и подсчетом токенов"""
        thread_id = None
        run_id = None
        
        try:
            # Получаем или создаем тред
            thread_id = await self.get_or_create_thread(user_id)
            
            # Логируем входящее сообщение
            await self.user_storage.log_message(
                user_id, message, "user", thread_id
            )
            
            # Добавляем сообщение в тред
            await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            
            # Запускаем ассистента
            run = await self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            run_id = run.id
            
            # Логируем запуск
            await self.user_storage.log_openai_activity(
                user_id, thread_id, run_id, "run_created"
            )
            
            # Ожидаем завершения
            while True:
                run_status = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                if run_status.status == "completed":
                    await self.user_storage.log_openai_activity(
                        user_id, thread_id, run_id, "completed"
                    )
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    error_msg = getattr(run_status, "last_error", None)
                    await self.user_storage.log_openai_activity(
                        user_id, thread_id, run_id, run_status.status, error_msg
                    )
                    logger.error(f"❌ Run failed for user_id={user_id}: {error_msg}")
                    yield "⚠️ Произошла ошибка при обработке запроса. Попробуйте еще раз."
                    return
                
                await asyncio.sleep(1)
            
            # Получаем ответ с информацией об использовании
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=1
            )
            
            if messages.data:
                assistant_message = messages.data[0]
                if assistant_message.content:
                    content = assistant_message.content[0]
                    if hasattr(content, 'text'):
                        response_text = content.text.value
                        
                        # Логируем ответ
                        await self.user_storage.log_message(
                            user_id, response_text, "assistant", 
                            thread_id, assistant_message.id
                        )
                        
                        # 🔥 ДОБАВЛЯЕМ ПОДСЧЕТ ТОКЕНОВ
                        try:
                            # Получаем информацию о использовании токенов из run
                            run_info = await self.client.beta.threads.runs.retrieve(
                                thread_id=thread_id,
                                run_id=run_id
                            )
                            
                            # Используем модель из run или дефолтную
                            model = getattr(run_info, 'model', 'gpt-4')
                            usage = getattr(run_info, 'usage', None)
                            
                            if usage:
                                await self.user_storage.add_token_usage(
                                    user_id=user_id,
                                    thread_id=thread_id,
                                    message_id=assistant_message.id,
                                    model=model,
                                    prompt_tokens=getattr(usage, 'prompt_tokens', 0),
                                    completion_tokens=getattr(usage, 'completion_tokens', 0),
                                    total_tokens=getattr(usage, 'total_tokens', 0)
                                )
                                logger.info(f"📊 Token usage recorded for user_id={user_id}: {getattr(usage, 'total_tokens', 0)} tokens")
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to record token usage for user_id={user_id}: {e}")
                        
                        # Stream ответ
                        for char in response_text:
                            yield char
                            await asyncio.sleep(0.01)
            
        except Exception as e:
            logger.error(f"❌ Error in process_message_streaming for user_id={user_id}: {e}")
            await self.user_storage.log_openai_activity(
                user_id, thread_id or "", run_id or "", "error", str(e)
            )
            yield "❌ Произошла ошибка. Попробуйте позже."
    
    async def process_prompt_streaming(self, prompt: str, model: str = "gpt-4.1") -> AsyncGenerator[str, None]:
        """Обрабатывает промпт напрямую через ChatCompletion с streaming"""
        try:
            logger.info(f"🚀 Processing prompt with model: {model}")
            
            # Создаем streaming запрос к ChatGPT
            stream = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                stream=True,
                temperature=0.7,
                max_tokens=2000
            )
            
            # Обрабатываем потоковый ответ
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"❌ Error in process_prompt_streaming: {e}")
            yield "❌ Произошла ошибка при генерации ответа. Попробуйте позже."
    
    async def process_message_fast(self, user_id: int, message: str) -> str:
        """Быстрая обработка сообщения без streaming с подсчетом токенов"""
        try:
            thread_id = await self.get_or_create_thread(user_id)
            
            # Логируем сообщение
            await self.user_storage.log_message(user_id, message, "user", thread_id)
            
            # Добавляем сообщение в тред
            await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            
            # Запускаем ассистента
            run = await self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            
            # Ожидаем завершения
            while True:
                run_status = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                
                if run_status.status == "completed":
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    error_msg = getattr(run_status, 'last_error', None)
                    logger.error(f"❌ Run failed for user_id={user_id}: {error_msg}")
                    return "⚠️ Произошла ошибка при обработке запроса."
                
                await asyncio.sleep(1)
            
            # Получаем ответ
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=1
            )
            
            if messages.data:
                assistant_message = messages.data[0]
                if assistant_message.content:
                    content = assistant_message.content[0]
                    if hasattr(content, 'text'):
                        response_text = content.text.value
                        
                        # Логируем ответ
                        await self.user_storage.log_message(
                            user_id, response_text, "assistant", 
                            thread_id, assistant_message.id
                        )
                        
                        # 🔥 ДОБАВЛЯЕМ ПОДСЧЕТ ТОКЕНОВ
                        try:
                            run_info = await self.client.beta.threads.runs.retrieve(
                                thread_id=thread_id,
                                run_id=run.id
                            )
                            
                            model = getattr(run_info, 'model', 'gpt-4')
                            usage = getattr(run_info, 'usage', None)
                            
                            if usage:
                                await self.user_storage.add_token_usage(
                                    user_id=user_id,
                                    thread_id=thread_id,
                                    message_id=assistant_message.id,
                                    model=model,
                                    prompt_tokens=getattr(usage, 'prompt_tokens', 0),
                                    completion_tokens=getattr(usage, 'completion_tokens', 0),
                                    total_tokens=getattr(usage, 'total_tokens', 0)
                                )
                                logger.info(f"📊 Token usage recorded for user_id={user_id}: {getattr(usage, 'total_tokens', 0)} tokens")
                        
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to record token usage for user_id={user_id}: {e}")
                        
                        return response_text
            
            return "⚠️ Не удалось получить ответ от ассистента."
            
        except Exception as e:
            logger.error(f"❌ Error in process_message_fast for user_id={user_id}: {e}")
            return "❌ Произошла ошибка. Попробуйте позже."