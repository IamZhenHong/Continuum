from __future__ import annotations

import os
from typing import Optional, Literal

from pydantic import BaseModel, BaseSettings, Field, SecretStr
from dotenv import load_dotenv
from openai import OpenAI
import redis
from supabase import create_client, Client

# ✅ Load environment variables from .env
load_dotenv()


class RedisSettings(BaseModel):
    REDIS_URL: str = "redis://localhost:6379/0"
    QUEUE_PROCESSING_COUNT: str = "queue:processing_count"
    QUEUE_ESTIMATED_TIME: str = "queue:estimated_time"
    RESOURCE_STATUS_PREFIX: str = "resource:status:"


class SupabaseSettings(BaseModel):
    SUPABASE_URL: str
    SUPABASE_KEY: SecretStr  # ✅ Stored securely


class TelegramSettings(BaseModel):
    TELEGRAM_BOT_TOKEN: SecretStr

    @property
    def TELEGRAM_API_URL(self) -> str:
        return f"https://api.telegram.org/bot{self.TELEGRAM_BOT_TOKEN.get_secret_value()}/sendMessage"


class OpenAISettings(BaseModel):
    OPENAI_API_KEY: SecretStr
    OPENAI_MODEL: Literal["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"] = "gpt-4o"


class FirecrawlSettings(BaseModel):
    FIRECRAWL_API_KEY: SecretStr


class DiffbotSettings(BaseModel):
    DIFFBOT_TOKEN: SecretStr


class Settings(BaseSettings):
    # ✅ App Metadata
    APP_NAME: str = "Hyperflow AI Assistant"
    APP_VERSION: str = "0.1.0"
    ENV: Literal["local", "dev", "prod"] = Field(default="dev")

    # ✅ External Services
    REDIS: RedisSettings = RedisSettings()
    SUPABASE: SupabaseSettings
    TELEGRAM: TelegramSettings
    OPENAI: OpenAISettings
    FIRECRAWL: FirecrawlSettings
    DIFFBOT: DiffbotSettings

    # ✅ Misc Settings
    DATA_RETENTION_DAYS: int = 30
    PROCESSING_TIME_ESTIMATE: int = 30  # Default estimated processing time

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# ✅ Initialize Settings
settings = Settings()

# ✅ Initialize OpenAI Client
openai_client = OpenAI(api_key=settings.OPENAI.OPENAI_API_KEY.get_secret_value())

# ✅ Initialize Redis Client
redis_client = redis.StrictRedis.from_url(settings.REDIS.REDIS_URL, decode_responses=True)

# ✅ Initialize Supabase Client
supabase_client: Client = create_client(
    settings.SUPABASE.SUPABASE_URL,
    settings.SUPABASE.SUPABASE_KEY.get_secret_value()
)

