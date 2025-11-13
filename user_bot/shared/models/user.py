from dataclasses import dataclass
from typing import Optional

@dataclass
class UserSession:
    """Модель пользовательской сессии"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # Позже добавим поля для OpenAI
    openai_thread_id: Optional[str] = None