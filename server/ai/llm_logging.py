import logging

from server.models.enums import LlmProvider

logger = logging.getLogger(__name__)


def log_llm_client_created(
    *,
    provider: LlmProvider,
    model: str,
    api_key_prefix: str,
) -> None:
    logger.info(
        "LLM client created: provider=%s model=%s api_key_prefix=%s...",
        provider.value,
        model,
        api_key_prefix,
    )


def log_skill_match_start(*, manager_user_id: int, project_id: int | None, length: int) -> None:
    logger.info(
        "Skill match started: manager_user_id=%s project_id=%s requirement_len=%s",
        manager_user_id,
        project_id,
        length,
    )


def log_skill_match_parsed(
    *,
    actionable: bool,
    weekly_hours: int | None,
    skill_count: int,
    summary: str,
) -> None:
    logger.info(
        "Skill match parsed: actionable=%s weekly_hours=%s skills=%s summary=%r",
        actionable,
        weekly_hours,
        skill_count,
        summary[:120],
    )


def log_skill_match_complete(
    *,
    ranked_count: int,
    llm_invoked: bool,
    message: str | None,
) -> None:
    logger.info(
        "Skill match complete: ranked=%s llm_invoked=%s message=%r",
        ranked_count,
        llm_invoked,
        message,
    )
