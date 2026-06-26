import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def disable_llm_for_tests(monkeypatch):
    monkeypatch.setenv("CHART_AGENT_LLM_MODE", "off")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
