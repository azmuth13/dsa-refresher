from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    LLM_PROVIDER: Literal["gemini", "groq"] = "groq"
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    PROBLEMS_FILE_PATH: str = "./data/problems.txt"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_SOLVED_PROBLEMS_TABLE: str = "solved_problems"
    LEETCODE_SUBMISSIONS_URL: str = "https://alfa-leetcode-api.onrender.com/suraj__k/submission"
    DAILY_MY_PROBLEM_TELEGRAM_ENABLED: bool = True
    DAILY_MY_PROBLEM_TELEGRAM_TIME: str = "06:00"
    DAILY_MY_PROBLEM_TELEGRAM_TIMEZONE: str = "Asia/Kolkata"
    CORS_ORIGINS: str = "http://localhost:5173"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_PARSE_MODE: str = "HTML"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
