import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel

LLMMode = Literal["off", "openai"]


class Settings(BaseModel):
    app_env: str = "development"
    llm_mode: LLMMode = "off"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", encoding="utf-8-sig")
    return Settings(
        app_env=os.getenv("CHART_AGENT_ENV", "development").strip().lower(),
        llm_mode=_read_llm_mode(),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
    )


def _read_llm_mode() -> LLMMode:
    value = os.getenv("CHART_AGENT_LLM_MODE", "off").strip().lower()
    if value == "openai":
        return "openai"
    return "off"
