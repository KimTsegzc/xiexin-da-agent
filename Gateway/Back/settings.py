from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]

# 支持的模型列表 —— 维护在代码里，前端从 get_model_list() 读取；
# 用户只需在 .env 中用 LLM_MODEL 指定当前选用的一个即可。
AVAILABLE_MODELS: list[str] = [
    "qwen3.5-plus",
    "qwen3-max",
    "qwen3.5-flash",
    "qwen-turbo",
    "glm-5"
]

_SOUL_FILE = REPO_ROOT / "soul.md"
_DEFAULT_SOUL = """你是谢鑫的数字分身。"""


def load_legacy_runtime_config() -> dict:
    """Load legacy runtime config from config.json when present."""
    config_path = REPO_ROOT / "config.json"
    if not config_path.exists():
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as fp:
            raw = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw, dict):
        return {}

    wrapped = raw.get("llm_provider_config")
    if isinstance(wrapped, dict):
        return wrapped
    return raw


def load_system_prompt() -> str:
    """每次调用时重新读取 soul.md，改完文件即时生效，无需重启。"""
    if _SOUL_FILE.exists():
        return _SOUL_FILE.read_text(encoding="utf-8").strip()
    return _DEFAULT_SOUL


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
        default=AVAILABLE_MODELS[-1],   # 默认末尾项；.env 里 LLM_MODEL 可覆盖
        validation_alias=AliasChoices("LLM_MODEL", "OPENAI_MODEL"),
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
    settings = Settings()
    if settings.api_key:
        return settings

    legacy = load_legacy_runtime_config()
    if not legacy:
        return settings

    updates = {
        key: legacy.get(key, getattr(settings, key))
        for key in ("api_key", "base_url", "model", "temperature", "top_p", "max_tokens")
    }
    return settings.model_copy(update=updates)


settings = get_settings()