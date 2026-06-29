from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.core.exceptions import LlmNotConfiguredError
from server.models.enums import NotificationType
from server.notifications.services.at_risk_notification_service import (
    AtRiskNotificationService,
)


def _project(*, with_manager: bool = True, with_user: bool = True):
    project = MagicMock()
    project.id = 5
    project.name = "Apollo"
    if not with_manager:
        project.manager = None
        return project
    manager = MagicMock()
    manager.id = 100
    manager.user = None
    if with_user:
        user = MagicMock()
        user.email = "mgr@example.com"
        user.full_name = "Mgr"
        manager.user = user
        manager.user.full_name = "Mgr"
    project.manager = manager
    return project


def _service(
    *,
    project_repo=None,
    milestone_repo=None,
    facts_service=None,
    help_service=None,
    notification_service=None,
) -> AtRiskNotificationService:
    return AtRiskNotificationService(
        project_repository=project_repo or AsyncMock(),
        milestone_repository=milestone_repo or AsyncMock(),
        project_facts_service=facts_service or AsyncMock(),
        help_suggestion_service=help_service or AsyncMock(),
        notification_service=notification_service or AsyncMock(),
    )


@pytest.mark.asyncio
async def test_notify_returns_false_when_project_missing():
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = None
    service = _service(project_repo=project_repo)

    assert await service.notify_project(1) is False


@pytest.mark.asyncio
async def test_notify_returns_false_when_manager_missing():
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = _project(with_manager=False)
    service = _service(project_repo=project_repo)

    assert await service.notify_project(1) is False


@pytest.mark.asyncio
async def test_notify_returns_false_when_manager_user_missing():
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = _project(with_user=False)
    service = _service(project_repo=project_repo)

    assert await service.notify_project(1) is False


@pytest.mark.asyncio
async def test_notify_sends_with_milestones_and_placeholder_summary():
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = _project()
    milestone_repo = AsyncMock()
    milestone = MagicMock()
    milestone.title = "M1"
    milestone.due_date = date(2026, 2, 1)
    milestone.status = "TODO"
    milestone_repo.find_by_project_id.return_value = [milestone]
    help_service = AsyncMock()
    help_service.suggest.return_value = "Ask bench for help"
    notification_service = AsyncMock()
    notification_service.send.return_value = True
    notification_service.get_config.return_value = None
    facts_service = AsyncMock()

    service = _service(
        project_repo=project_repo,
        milestone_repo=milestone_repo,
        facts_service=facts_service,
        help_service=help_service,
        notification_service=notification_service,
    )

    assert await service.notify_project(5) is True
    intent = notification_service.send.await_args.args[0]
    assert intent.notification_type == NotificationType.PROJECT_AT_RISK
    assert intent.dedupe_key == "project:5:at_risk"
    assert intent.to_email == "mgr@example.com"
    assert "AI risk summary is not available" in intent.body
    assert "M1" in intent.body


@pytest.mark.asyncio
async def test_notify_uses_no_milestones_message():
    project_repo = AsyncMock()
    project_repo.get_by_id_with_manager.return_value = _project()
    milestone_repo = AsyncMock()
    milestone_repo.find_by_project_id.return_value = []
    help_service = AsyncMock()
    help_service.suggest.return_value = "n/a"
    notification_service = AsyncMock()
    notification_service.send.return_value = True
    notification_service.get_config.return_value = None

    service = _service(
        project_repo=project_repo,
        milestone_repo=milestone_repo,
        help_service=help_service,
        notification_service=notification_service,
    )

    await service.notify_project(5)
    body = notification_service.send.await_args.args[0].body
    assert "No milestones defined." in body


@pytest.mark.asyncio
async def test_build_ai_summary_returns_placeholder_when_config_missing():
    notification_service = AsyncMock()
    notification_service.get_config.return_value = None
    facts_service = AsyncMock()
    facts_service.collect.return_value = MagicMock(to_prompt_text=lambda: "facts")
    service = _service(
        facts_service=facts_service,
        notification_service=notification_service,
    )

    summary = await service._build_ai_summary(1, 100)

    assert summary == AtRiskNotificationService._AI_PLACEHOLDER


@pytest.mark.asyncio
async def test_build_ai_summary_returns_placeholder_when_credentials_none():
    notification_service = AsyncMock()
    notification_service.get_config.return_value = MagicMock()
    facts_service = AsyncMock()
    facts_service.collect.return_value = MagicMock(to_prompt_text=lambda: "facts")
    service = _service(
        facts_service=facts_service,
        notification_service=notification_service,
    )

    with patch(
        "server.notifications.services.at_risk_notification_service.resolve_llm_credentials",
        return_value=None,
    ):
        summary = await service._build_ai_summary(1, 100)

    assert summary == AtRiskNotificationService._AI_PLACEHOLDER


@pytest.mark.asyncio
async def test_build_ai_summary_success_path():
    notification_service = AsyncMock()
    notification_service.get_config.return_value = MagicMock()
    facts = MagicMock()
    facts.to_prompt_text.return_value = "facts text"
    facts_service = AsyncMock()
    facts_service.collect.return_value = facts
    service = _service(
        facts_service=facts_service,
        notification_service=notification_service,
    )

    with (
        patch(
            "server.notifications.services.at_risk_notification_service.resolve_llm_credentials",
            return_value=("GEMINI", "secret-key"),
        ),
        patch("server.ai.llm_factory.LLMFactory") as factory_cls,
        patch("server.ai.chains.risk_summary_chain.RiskSummaryChain") as chain_cls,
    ):
        factory_cls.return_value.create.return_value = MagicMock()
        chain_cls.return_value.invoke.return_value = "Risk looks elevated"

        summary = await service._build_ai_summary(1, 100)

    assert summary == "Risk looks elevated"


@pytest.mark.asyncio
async def test_build_ai_summary_handles_llm_not_configured():
    facts_service = AsyncMock()
    facts_service.collect.side_effect = LlmNotConfiguredError("no llm")
    service = _service(facts_service=facts_service)

    summary = await service._build_ai_summary(1, 100)

    assert summary == AtRiskNotificationService._AI_PLACEHOLDER


@pytest.mark.asyncio
async def test_build_ai_summary_handles_generic_exception():
    facts_service = AsyncMock()
    facts_service.collect.side_effect = RuntimeError("boom")
    service = _service(facts_service=facts_service)

    summary = await service._build_ai_summary(1, 100)

    assert summary == AtRiskNotificationService._AI_PLACEHOLDER
