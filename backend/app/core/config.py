import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel

LLMMode = Literal["off", "openai"]


class Settings(BaseModel):
    llm_mode: LLMMode = "off"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        llm_mode=_read_llm_mode(),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )


def _read_llm_mode() -> LLMMode:
    value = os.getenv("CHART_AGENT_LLM_MODE", "off").strip().lower()
    if value == "openai":
        return "openai"
    return "off"
