import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

@dataclass
class Config:
    # Telegram
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    
    # OpenAI (для статистики, если понадобится)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # PostgreSQL Database (SHARED)
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: str = os.getenv("DB_PORT", "")
    DB_NAME: str = os.getenv("DB_NAME", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    
    # Super Admin
    SUPER_ADMIN_ID: int = int(os.getenv("SUPER_ADMIN_ID", "0"))
    
    # Admin Channel
    ADMIN_CHANNEL_ID: int = int(os.getenv("ADMIN_CHANNEL_ID", "0"))
    ADMIN_CHANNEL_LINK: str = os.getenv("ADMIN_CHANNEL_LINK", "")
    
    # Настройки
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "5"))
    
    @property
    def database_url(self) -> str:
        """Возвращает URL для подключения к PostgreSQL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def validate(self):
        """Проверка обязательных переменных"""
        required_vars = {
            "TELEGRAM_TOKEN": self.TELEGRAM_TOKEN,
            "DB_HOST": self.DB_HOST,
            "DB_PORT": self.DB_PORT,
            "DB_NAME": self.DB_NAME,
            "DB_USER": self.DB_USER,
            "DB_PASSWORD": self.DB_PASSWORD,
            "SUPER_ADMIN_ID": self.SUPER_ADMIN_ID,
            "ADMIN_CHANNEL_ID": self.ADMIN_CHANNEL_ID
        }
        
        for var_name, var_value in required_vars.items():
            if not var_value:
                raise ValueError(f"{var_name} is required")

config = Config()
