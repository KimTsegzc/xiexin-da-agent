from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DASHSCOPE_API_KEY",
            "ALIYUN_BAILIAN_API_KEY",
            "OPENAI_API_KEY",
            "API_KEY",
        ),
    )
    base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias=AliasChoices(
            "DASHSCOPE_BASE_URL",
            "ALIYUN_BAILIAN_BASE_URL",
            "OPENAI_BASE_URL",
            "BASE_URL",
        ),
    )
    model: str = Field(
        default="qwen3.5-flash",
        validation_alias=AliasChoices("LLM_MODEL", "MODEL", "OPENAI_MODEL"),
    )
    system_prompt: str = Field(
        default="You are a helpful assistant.",
        validation_alias=AliasChoices("LLM_SYSTEM_PROMPT", "SYSTEM_PROMPT"),
    )
    temperature: float | None = Field(
        default=0.7,
        validation_alias=AliasChoices("LLM_TEMPERATURE", "TEMPERATURE"),
    )
    top_p: float | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_TOP_P", "TOP_P"),
    )
    max_tokens: int | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_MAX_TOKENS", "MAX_TOKENS"),
    )

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()