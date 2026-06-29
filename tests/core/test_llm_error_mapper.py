from server.ai.llm_error_mapper import LlmErrorMapper


def test_user_message_for_invalid_api_key():
    message = LlmErrorMapper.user_message(
        Exception("API key not valid. Please pass a valid API key."),
        "skill match",
    )
    assert "LLM API key is invalid" in message
    assert "Google AI Studio" in message


def test_user_message_for_api_key_invalid_code():
    message = LlmErrorMapper.user_message(
        Exception("api_key_invalid"),
        "team build",
    )
    assert "LLM API key is invalid" in message


def test_user_message_for_quota_exceeded():
    message = LlmErrorMapper.user_message(
        Exception("ResourceExhausted: quota exceeded"),
        "skill match",
    )
    assert "LLM quota exceeded" in message


def test_user_message_for_http_429():
    message = LlmErrorMapper.user_message(Exception("HTTP 429 Too Many Requests"), "op")
    assert "LLM quota exceeded" in message


def test_user_message_for_model_not_found():
    message = LlmErrorMapper.user_message(
        Exception("Model gemini-xyz not found"),
        "skill match",
    )
    assert "LLM model not found" in message
    assert "GEMINI_MODEL" in message


def test_user_message_for_generic_error():
    message = LlmErrorMapper.user_message(Exception("connection reset"), "skill match")
    assert message == "AI skill match failed. Check server logs for details."


def test_log_summary_includes_exception_type_and_message():
    summary = LlmErrorMapper.log_summary(ValueError("boom"))
    assert summary == "ValueError: boom"
