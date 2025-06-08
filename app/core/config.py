from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


class Settings(BaseSettings):
    # Database settings
    database_url: str = Field(..., env="DATABASE_URL")
    async_database_url: Optional[str] = Field(None, env="ASYNC_DATABASE_URL")
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD") 
    db_name: str = Field(..., env="DB_NAME")
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    
    # API Security
    api_key: str = Field(default="your-secret-api-key", env="API_KEY")
    
    # Application settings
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Organization API"
    project_version: str = "1.0.0"
    project_description: str = "REST API для справочника организаций, зданий и деятельности"
    
    @validator('async_database_url', always=True)
    def build_async_database_url(cls, v, values):
        if v:
            return v
        # Преобразуем обычный URL в async URL для asyncpg
        db_url = values.get('database_url', '')
        if db_url.startswith('postgresql://'):
            return db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return db_url
    
    @property
    def sync_database_url(self) -> str:
        """Синхронный URL для Alembic и других синхронных операций"""
        return self.database_url
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Создаем единственный экземпляр настроек
settings = Settings()