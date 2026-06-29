from unittest.mock import MagicMock, patch

import pytest

from server.ai.llm_factory import LLMFactory
from server.core.exceptions import LlmInvocationError
from server.models.enums import LlmProvider


def _settings(*, gemini: str = "gemini-custom", groq: str = "groq-custom"):
    return MagicMock(gemini_model=gemini, groq_model=groq)


@patch("server.ai.llm_factory.ChatGoogleGenerativeAI")
@patch("server.ai.llm_factory.get_settings")
@patch("server.ai.llm_factory.log_llm_client_created")
def test_create_gemini(mock_log, mock_settings, mock_gemini):
    mock_settings.return_value = _settings()
    client = MagicMock()
    mock_gemini.return_value = client

    result = LLMFactory().create(LlmProvider.GEMINI, "abcdefghijklmnop")

    assert result is client
    mock_gemini.assert_called_once()
    kwargs = mock_gemini.call_args.kwargs
    assert kwargs["model"] == "gemini-custom"
    assert kwargs["google_api_key"] == "abcdefghijklmnop"
    mock_log.assert_called_once()


@patch("server.ai.llm_factory.ChatGroq")
@patch("server.ai.llm_factory.get_settings")
@patch("server.ai.llm_factory.log_llm_client_created")
def test_create_groq(mock_log, mock_settings, mock_groq):
    mock_settings.return_value = _settings()
    client = MagicMock()
    mock_groq.return_value = client

    result = LLMFactory().create(LlmProvider.GROQ, "key12345xxxx")

    assert result is client
    kwargs = mock_groq.call_args.kwargs
    assert kwargs["model"] == "groq-custom"
    assert kwargs["api_key"] == "key12345xxxx"


@patch("server.ai.llm_factory.ChatGoogleGenerativeAI")
@patch("server.ai.llm_factory.get_settings")
def test_create_uses_default_model_when_blank(mock_settings, mock_gemini):
    mock_settings.return_value = _settings(gemini="  ", groq="")
    LLMFactory().create(LlmProvider.GEMINI, "abcdefgh")
    assert (
        mock_gemini.call_args.kwargs["model"] == LLMFactory.DEFAULT_GEMINI_MODEL
    )


@patch("server.ai.llm_factory.get_settings")
def test_create_unsupported_provider_raises(mock_settings):
    mock_settings.return_value = _settings()
    with pytest.raises(LlmInvocationError, match="Unsupported"):
        LLMFactory().create(MagicMock(value="OTHER"), "abcdefgh")


@patch("server.ai.llm_factory.ChatGoogleGenerativeAI", side_effect=RuntimeError("boom"))
@patch("server.ai.llm_factory.get_settings")
def test_create_wraps_init_errors(mock_settings, _mock_gemini):
    mock_settings.return_value = _settings()
    with pytest.raises(LlmInvocationError, match="Failed to initialize"):
        LLMFactory().create(LlmProvider.GEMINI, "abcdefgh")
