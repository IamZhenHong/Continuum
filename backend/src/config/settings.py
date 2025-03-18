import os
from pydantic import  Field, SecretStr
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from openai import OpenAI
import redis
from supabase import create_client, Client

# ✅ Load environment variables from .env file
load_dotenv()


class RedisSettings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_QUEUE_PROCESSING_COUNT: str = "queue:processing_count"
    REDIS_QUEUE_ESTIMATED_TIME: str = "queue:estimated_time"
    REDIS_RESOURCE_STATUS_PREFIX: str = "resource:status:"


class SupabaseSettings(BaseSettings):
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_KEY: SecretStr = Field(..., env="SUPABASE_KEY")


class TelegramSettings(BaseSettings):
    TELEGRAM_BOT_TOKEN: SecretStr = Field(..., env="TELEGRAM_BOT_TOKEN")

    @property
    def TELEGRAM_API_URL(self) -> str:
        return f"https://api.telegram.org/bot{self.TELEGRAM_BOT_TOKEN.get_secret_value()}/sendMessage"


class OpenAISettings(BaseSettings):
    OPENAI_API_KEY: SecretStr = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = "gpt-4o"


class FirecrawlSettings(BaseSettings):
    FIRECRAWL_API_KEY: SecretStr = Field(..., env="FIRECRAWL_API_KEY")


class DiffbotSettings(BaseSettings):
    DIFFBOT_TOKEN: SecretStr = Field(..., env="DIFFBOT_TOKEN")


class Settings(BaseSettings):
    # ✅ App Metadata
    APP_NAME: str = "Hyperflow AI Assistant"
    APP_VERSION: str = "0.1.0"
    ENV: str = Field(default="dev", env="ENV")
    APP_BASE_URL: str = Field(default="http://localhost:8000", env="APP_BASE_URL")

      # ✅ CORS Settings
    ALLOWED_ORIGINS: list[str] = Field(default=["*"], env="ALLOWED_ORIGINS")  # Allow all by default

    # ✅ External Services
    REDIS: RedisSettings = RedisSettings()
    SUPABASE: SupabaseSettings = SupabaseSettings()
    TELEGRAM: TelegramSettings = TelegramSettings()
    OPENAI: OpenAISettings = OpenAISettings()
    FIRECRAWL: FirecrawlSettings = FirecrawlSettings()
    DIFFBOT: DiffbotSettings = DiffbotSettings()

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

# ✅ Debugging: Print Loaded Settings
print("🔹 Loaded Settings:", settings.dict(exclude={"SUPABASE.SUPABASE_KEY", "TELEGRAM.TELEGRAM_BOT_TOKEN", "OPENAI.OPENAI_API_KEY", "FIRECRAWL.FIRECRAWL_API_KEY", "DIFFBOT.DIFFBOT_TOKEN"}))  # Hide secrets
