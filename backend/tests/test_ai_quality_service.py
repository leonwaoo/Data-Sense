from app.services.ai_quality_service import _has_real_api_key


def test_placeholder_api_key_does_not_enable_ai() -> None:
    assert not _has_real_api_key("")
    assert not _has_real_api_key("sua_chave_openai")
    assert not _has_real_api_key("sua_chave_openrouter")
    assert not _has_real_api_key("YOUR_OPENAI_API_KEY")
    assert not _has_real_api_key("YOUR_OPENROUTER_API_KEY")
    assert _has_real_api_key("sk-proj-chave-real-de-teste")
