from server.ai.services.project_facts_service import ProjectFactsService
from server.core.exceptions import LlmNotConfiguredError
from server.core.llm_config_resolver import resolve_llm_credentials
from server.models.enums import HealthStatus, NotificationType
from server.notifications.dto.notification_dto import NotificationIntent, ProjectAtRiskContext
from server.notifications.services.at_risk_help_suggestion_service import (
    AtRiskHelpSuggestionService,
)
from server.notifications.services.health_status_mapper import HealthStatusMapper
from server.notifications.services.notification_service import NotificationService
from server.notifications.templates.email_templates import EmailTemplateRenderer
from server.repositories.milestone_repository import MilestoneRepository
from server.repositories.project_repository import ProjectRepository
from server.services.resource_mapper import ResourceMapper


class AtRiskNotificationService:
    _AI_PLACEHOLDER = (
        "AI risk summary is not available (LLM not configured). "
        "Review milestones and timesheet hours in the PRM console."
    )

    def __init__(
        self,
        project_repository: ProjectRepository,
        milestone_repository: MilestoneRepository,
        project_facts_service: ProjectFactsService,
        help_suggestion_service: AtRiskHelpSuggestionService,
        notification_service: NotificationService,
    ) -> None:
        self._project_repository = project_repository
        self._milestone_repository = milestone_repository
        self._project_facts_service = project_facts_service
        self._help_suggestion_service = help_suggestion_service
        self._notification_service = notification_service

    async def notify_project(self, project_id: int) -> bool:
        project = await self._project_repository.get_by_id_with_manager(project_id)
        if project is None or project.manager is None or project.manager.user is None:
            return False

        manager = project.manager
        manager_email = manager.user.email
        manager_name = ResourceMapper.full_name(manager)

        milestones = await self._milestone_repository.find_by_project_id(project_id)
        milestone_lines = [
            f"- {milestone.title} (due {milestone.due_date}, {milestone.status})"
            for milestone in milestones[:10]
        ]
        milestones_summary = (
            "\n".join(milestone_lines) if milestone_lines else "No milestones defined."
        )

        ai_summary = await self._build_ai_summary(project_id, manager.id)
        suggested_help = await self._help_suggestion_service.suggest(project_id)

        subject, body = EmailTemplateRenderer.project_at_risk(
            ProjectAtRiskContext(
                project_name=project.name,
                manager_name=manager_name,
                milestones_summary=milestones_summary,
                health_standing=HealthStatusMapper.to_traffic_light(
                    HealthStatus.AT_RISK
                ),
                ai_summary=ai_summary,
                suggested_help=suggested_help,
            )
        )

        return await self._notification_service.send(
            NotificationIntent(
                notification_type=NotificationType.PROJECT_AT_RISK,
                dedupe_key=f"project:{project_id}:at_risk",
                to_email=manager_email,
                subject=subject,
                body=body,
                entity_type="project",
                entity_id=project_id,
            )
        )

    async def _build_ai_summary(self, project_id: int, manager_resource_id: int) -> str:
        try:
            facts = await self._project_facts_service.collect(
                project_id, manager_resource_id
            )
            from server.ai.chains.risk_summary_chain import RiskSummaryChain
            from server.ai.llm_factory import LLMFactory

            config = await self._notification_service.get_config()
            if config is None:
                return self._AI_PLACEHOLDER
            resolved = resolve_llm_credentials(config)
            if resolved is None:
                return self._AI_PLACEHOLDER
            provider, api_key = resolved

            llm = LLMFactory().create(provider, api_key)
            return RiskSummaryChain(llm).invoke(facts.to_prompt_text())
        except LlmNotConfiguredError:
            return self._AI_PLACEHOLDER
        except Exception:
            return self._AI_PLACEHOLDER
