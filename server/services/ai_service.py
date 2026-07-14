import asyncio
import logging

from server.ai.chains.parse_skill_match_requirement_chain import (
    ParseSkillMatchRequirementChain,
)
from server.ai.graphs.risk_summary_graph import RiskSummaryGraphRunner
from server.ai.graphs.skill_match_graph import SkillMatchGraphRunner
from server.ai.graphs.team_build_graph import TeamBuildGraphRunner
from server.ai.llm_error_mapper import LlmErrorMapper
from server.ai.llm_factory import LLMFactory
from server.ai.llm_logging import (
    log_skill_match_complete,
    log_skill_match_parsed,
    log_skill_match_start,
)
from server.ai.nodes.team_build_nodes import MAX_TEAM_ROLES
from server.ai.services.availability_date_service import AvailabilityDateService
from server.ai.services.project_facts_service import ProjectFactsService
from server.ai.services.skill_match_candidate_service import SkillMatchCandidateService
from server.ai.services.skill_match_requirement_evaluator import (
    SkillMatchRequirementEvaluator,
)
from server.ai.services.team_build_candidate_service import TeamBuildCandidateService
from server.ai.services.team_diagnostics_service import TeamDiagnosticsService
from server.ai.services.team_gap_analyzer import TeamGapAnalyzer
from server.core.exceptions import (
    InvalidSkillMatchRequestError,
    InvalidTeamBuildRequestError,
    LlmInvocationError,
    ManagerProfileNotFoundError,
    ProjectNotFoundError,
)
from server.models.user import User
from server.repositories.project_repository import ProjectRepository
from server.repositories.resource_repository import ResourceRepository
from server.schemas.requests.ai import SkillMatchRequest, TeamBuildRequest
from server.schemas.responses.ai import (
    ParsedTeamRoleResponse,
    RiskSummaryResponse,
    SkillMatchCandidateResponse,
    SkillMatchResponse,
    TeamBuildResponse,
    TeamRoleGapResponse,
    TeamRoleMatchResponse,
)
from server.services.manager_team_service import ManagerTeamService
from server.services.system_config_service import SystemConfigService

RISK_SUMMARY_DISCLAIMER = (
    "This summary is AI-generated from milestone and timesheet data."
)
TEAM_BUILD_DISCLAIMER = "AI-generated team suggestions — verify before allocating."

logger = logging.getLogger(__name__)


class AIService:
    _NO_CANDIDATES_MESSAGE = (
        "No employees with enough free capacity for this requirement"
    )
    _VAGUE_REQUIREMENT_MESSAGE = (
        "Could not identify a specific role, skill, category, or weekly hours "
        "from your requirement. Please add more detail and try again."
    )

    def __init__(
        self,
        system_config_service: SystemConfigService,
        resource_repository: ResourceRepository,
        project_repository: ProjectRepository,
        candidate_service: SkillMatchCandidateService,
        project_facts_service: ProjectFactsService,
        llm_factory: LLMFactory,
        team_build_candidate_service: TeamBuildCandidateService,
        team_diagnostics_service: TeamDiagnosticsService,
        team_gap_analyzer: TeamGapAnalyzer,
        manager_team_service: ManagerTeamService,
        skill_match_runner: SkillMatchGraphRunner | None = None,
        risk_summary_runner: RiskSummaryGraphRunner | None = None,
        team_build_runner: TeamBuildGraphRunner | None = None,
    ) -> None:
        self._system_config_service = system_config_service
        self._resource_repository = resource_repository
        self._project_repository = project_repository
        self._candidate_service = candidate_service
        self._project_facts_service = project_facts_service
        self._llm_factory = llm_factory
        self._team_build_candidate_service = team_build_candidate_service
        self._team_diagnostics_service = team_diagnostics_service
        self._team_gap_analyzer = team_gap_analyzer
        self._manager_team_service = manager_team_service
        self._requirement_evaluator = SkillMatchRequirementEvaluator()
        self._skill_match_runner = skill_match_runner or SkillMatchGraphRunner()
        self._risk_summary_runner = risk_summary_runner or RiskSummaryGraphRunner()
        self._team_build_runner = team_build_runner or TeamBuildGraphRunner(
            gap_analyzer=team_gap_analyzer
        )

    async def skill_match(
        self, user: User, request: SkillMatchRequest
    ) -> SkillMatchResponse:
        requirement = request.requirement.strip()
        if len(requirement) < 10:
            raise InvalidSkillMatchRequestError(
                "Requirement must be at least 10 characters"
            )

        manager_resource_id = await self._resolve_manager_resource_id(user)
        if request.project_id is not None:
            await self._ensure_project_owned(request.project_id, manager_resource_id)

        log_skill_match_start(
            manager_user_id=user.id,
            project_id=request.project_id,
            length=len(requirement),
        )

        llm_config = await self._system_config_service.get_llm_config()
        llm = self._llm_factory.create(llm_config.provider, llm_config.api_key)

        try:
            parsed_output = await asyncio.to_thread(
                ParseSkillMatchRequirementChain(llm).invoke, requirement
            )
        except Exception as exc:
            self._raise_llm_error("requirement parsing", exc)

        parsed_requirement = self._requirement_evaluator.evaluate(
            parsed_output,
            max_weekly_hours=llm_config.max_weekly_hours,
        )
        log_skill_match_parsed(
            actionable=parsed_requirement.is_actionable,
            weekly_hours=parsed_requirement.weekly_hours,
            skill_count=len(parsed_requirement.skill_names),
            summary=parsed_requirement.summary,
        )

        if not parsed_requirement.is_actionable:
            logger.info("Skill match stopped: requirement not actionable")
            return self._build_skill_match_response(
                items=[],
                message=self._VAGUE_REQUIREMENT_MESSAGE,
                llm_invoked=False,
                weekly_hours_requested=None,
                requirement_parse_invoked=True,
                parsed_summary=parsed_requirement.summary,
            )

        candidates = await self._candidate_service.load_for_manager(
            manager_resource_id,
            max_weekly_hours=llm_config.max_weekly_hours,
        )

        if not candidates:
            return self._build_skill_match_response(
                items=[],
                message=self._NO_CANDIDATES_MESSAGE,
                llm_invoked=False,
                weekly_hours_requested=parsed_requirement.weekly_hours,
                requirement_parse_invoked=True,
                parsed_summary=parsed_requirement.summary,
            )

        initial_state = {
            "requirement": requirement,
            "project_id": request.project_id,
            "candidates": candidates,
            "parsed_requirement": parsed_requirement,
            "weekly_hours": parsed_requirement.weekly_hours,
            "max_weekly_hours": llm_config.max_weekly_hours,
            "llm": llm,
            "llm_invoked": False,
            "ranked_items": [],
        }
        try:
            final_state = await asyncio.to_thread(
                self._skill_match_runner.invoke, initial_state
            )
        except Exception as exc:
            self._raise_llm_error("candidate ranking", exc)

        items = [
            SkillMatchCandidateResponse(
                resource_id=row["resource_id"],
                resource_name=row["resource_name"],
                reason=row["reason"],
                free_hours_per_week=row.get("free_hours_per_week"),
                suggested_utilisation_percent=row.get("suggested_utilisation_percent"),
                rank=row["rank"],
            )
            for row in final_state.get("ranked_items", [])
        ]

        log_skill_match_complete(
            ranked_count=len(items),
            llm_invoked=bool(final_state.get("llm_invoked")),
            message=final_state.get("message"),
        )

        return self._build_skill_match_response(
            items=items,
            message=final_state.get("message"),
            llm_invoked=bool(final_state.get("llm_invoked")),
            weekly_hours_requested=final_state.get("weekly_hours"),
            requirement_parse_invoked=True,
            parsed_summary=parsed_requirement.summary,
        )

    async def team_build(
        self, user: User, request: TeamBuildRequest
    ) -> TeamBuildResponse:
        requirement = request.requirement.strip()
        if len(requirement) < 10:
            raise InvalidTeamBuildRequestError(
                "Requirement must be at least 10 characters"
            )

        manager_resource_id = await self._resolve_manager_resource_id(user)
        await self._ensure_project_owned(request.project_id, manager_resource_id)

        llm_config = await self._system_config_service.get_llm_config()
        llm = self._llm_factory.create(llm_config.provider, llm_config.api_key)
        logger.info(
            "Team build started: manager_user_id=%s project_id=%s",
            user.id,
            request.project_id,
        )

        bench_candidates = await self._team_build_candidate_service.load_bench_for_manager(
            manager_resource_id
        )
        diagnostics = await self._team_diagnostics_service.load_for_manager(
            manager_resource_id
        )

        final_state = await self._team_build_runner.invoke(
            {
                "requirement": requirement,
                "project_id": request.project_id,
                "max_roles": MAX_TEAM_ROLES,
                "bench_candidates": bench_candidates,
                "diagnostics": diagnostics,
                "llm": llm,
                "llm_invoked": False,
            }
        )
        logger.info(
            "Team build complete: roles=%s matches=%s gaps=%s llm_invoked=%s",
            len(final_state.get("parsed_roles", [])),
            len(final_state.get("assignments", [])),
            len(final_state.get("gaps", [])),
            bool(final_state.get("llm_invoked")),
        )

        parsed_roles = [
            ParsedTeamRoleResponse(
                role_key=role.role_key,
                role_title=role.role_title,
                skill_names=role.skill_names,
                skill_category=role.skill_category,
                min_proficiency=role.min_proficiency,
            )
            for role in final_state.get("parsed_roles", [])
        ]
        matches = [
            TeamRoleMatchResponse(
                role_key=assignment.role_key,
                role_title=assignment.role_title,
                resource_id=assignment.resource_id,
                resource_name=assignment.resource_name,
                reason=assignment.reason,
                match_score=assignment.match_score,
            )
            for assignment in final_state.get("assignments", [])
        ]
        gaps = [
            TeamRoleGapResponse(
                role_key=gap.role_key,
                role_title=gap.role_title,
                gap_type=gap.gap_type.value,
                message=gap.message,
                available_from=gap.available_from,
                candidate_hint_name=gap.candidate_hint_name,
            )
            for gap in final_state.get("gaps", [])
        ]

        return TeamBuildResponse(
            project_id=request.project_id,
            parsed_roles=parsed_roles,
            matches=matches,
            gaps=gaps,
            llm_invoked=bool(final_state.get("llm_invoked")),
            disclaimer=TEAM_BUILD_DISCLAIMER,
        )

    async def risk_summary(self, user: User, project_id: int) -> RiskSummaryResponse:
        manager_resource_id = await self._resolve_manager_resource_id(user)
        llm_config = await self._system_config_service.get_llm_config()
        llm = self._llm_factory.create(llm_config.provider, llm_config.api_key)
        logger.info(
            "Risk summary started: manager_user_id=%s project_id=%s",
            user.id,
            project_id,
        )

        facts = await self._project_facts_service.collect(
            project_id, manager_resource_id
        )

        final_state = await asyncio.to_thread(
            self._risk_summary_runner.invoke,
            {
                "project_id": project_id,
                "project_name": facts.project_name,
                "facts_text": facts.to_prompt_text(),
                "llm": llm,
                "llm_invoked": False,
            },
        )
        logger.info(
            "Risk summary complete: project_id=%s llm_invoked=%s summary_len=%s",
            project_id,
            bool(final_state.get("llm_invoked")),
            len(final_state.get("summary", "")),
        )

        return RiskSummaryResponse(
            project_id=project_id,
            project_name=facts.project_name,
            summary=final_state.get("summary", ""),
            disclaimer=RISK_SUMMARY_DISCLAIMER,
            llm_invoked=bool(final_state.get("llm_invoked")),
        )

    async def _resolve_manager_resource_id(self, user: User) -> int:
        return await self._manager_team_service.resolve_manager_resource_id(user)

    async def _ensure_project_owned(
        self, project_id: int, manager_resource_id: int
    ) -> None:
        project = await self._project_repository.get_by_id_with_manager(project_id)
        if project is None or project.manager_id != manager_resource_id:
            raise ProjectNotFoundError("Project not found")

    @staticmethod
    def _raise_llm_error(operation: str, exc: Exception) -> None:
        logger.error(
            "AI %s failed: %s",
            operation,
            LlmErrorMapper.log_summary(exc),
            exc_info=True,
        )
        raise LlmInvocationError(LlmErrorMapper.user_message(exc, operation)) from exc

    @staticmethod
    def _build_skill_match_response(
        *,
        items: list[SkillMatchCandidateResponse],
        message: str | None,
        llm_invoked: bool,
        weekly_hours_requested: int | None,
        requirement_parse_invoked: bool,
        parsed_summary: str | None,
    ) -> SkillMatchResponse:
        return SkillMatchResponse(
            items=items,
            message=message,
            llm_invoked=llm_invoked,
            weekly_hours_requested=weekly_hours_requested,
            requirement_parse_invoked=requirement_parse_invoked,
            parsed_summary=parsed_summary,
        )
