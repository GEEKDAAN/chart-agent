from app.core.config import get_settings


def test_openai_base_url_is_loaded_from_environment(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("CHART_AGENT_LLM_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.5")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://ai.allrealai.com/v1")

    settings = get_settings()

    assert settings.llm_mode == "openai"
    assert settings.openai_api_key == "test-key"
    assert settings.openai_model == "gpt-5.5"
    assert settings.openai_base_url == "https://ai.allrealai.com/v1"
    get_settings.cache_clear()
