import logging

from server.ai.llm_logging import (
    log_llm_client_created,
    log_skill_match_complete,
    log_skill_match_parsed,
    log_skill_match_start,
)
from server.models.enums import LlmProvider


def test_log_llm_client_created(caplog):
    with caplog.at_level(logging.INFO, logger="server.ai.llm_logging"):
        log_llm_client_created(
            provider=LlmProvider.GEMINI,
            model="gemini-2.0-flash",
            api_key_prefix="abcd1234",
        )
    assert "LLM client created" in caplog.text
    assert "GEMINI" in caplog.text
    assert "abcd1234" in caplog.text


def test_log_skill_match_start(caplog):
    with caplog.at_level(logging.INFO, logger="server.ai.llm_logging"):
        log_skill_match_start(manager_user_id=7, project_id=3, length=42)
    assert "Skill match started" in caplog.text
    assert "manager_user_id=7" in caplog.text


def test_log_skill_match_parsed(caplog):
    with caplog.at_level(logging.INFO, logger="server.ai.llm_logging"):
        log_skill_match_parsed(
            actionable=True,
            weekly_hours=20,
            skill_count=2,
            summary="Need React help" * 20,
        )
    assert "Skill match parsed" in caplog.text
    assert "actionable=True" in caplog.text


def test_log_skill_match_complete(caplog):
    with caplog.at_level(logging.INFO, logger="server.ai.llm_logging"):
        log_skill_match_complete(
            ranked_count=3,
            llm_invoked=True,
            message="done",
        )
    assert "Skill match complete" in caplog.text
    assert "ranked=3" in caplog.text
