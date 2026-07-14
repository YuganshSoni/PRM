from datetime import date
from unittest.mock import AsyncMock

import pytest

from server.ai.dto.team_build import (
    RoleRequirementDTO,
    SkillProficiencyDTO,
    TeamDiagnosticMemberDTO,
    TeamGapType,
)
from server.ai.services.team_gap_analyzer import TeamGapAnalyzer
from server.models.enums import ProficiencyLevel, SkillCategoryEnum


def _role(
    key: str = "backend",
    skill_names: list[str] | None = None,
    skill_category: SkillCategoryEnum | None = None,
) -> RoleRequirementDTO:
    return RoleRequirementDTO(
        role_key=key,
        role_title=key.title(),
        skill_names=skill_names or (["Python"] if skill_category is None else []),
        skill_category=skill_category,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
    )


def _member(
    resource_id: int,
    name: str,
    *,
    is_bench: bool,
    skills: list[SkillProficiencyDTO] | None = None,
) -> TeamDiagnosticMemberDTO:
    return TeamDiagnosticMemberDTO(
        resource_id=resource_id,
        resource_name=name,
        is_bench=is_bench,
        skills=skills
        or [
            SkillProficiencyDTO(
                skill_name="Python",
                category=SkillCategoryEnum.BACKEND,
                proficiency=ProficiencyLevel.INTERMEDIATE,
            )
        ],
    )


@pytest.mark.asyncio
async def test_skill_absence_when_no_one_has_skill():
    analyzer = TeamGapAnalyzer()
    role = _role()
    diagnostics = [
        _member(
            1,
            "Ada",
            is_bench=True,
            skills=[
                SkillProficiencyDTO(
                    skill_name="Go",
                    category=SkillCategoryEnum.BACKEND,
                    proficiency=ProficiencyLevel.INTERMEDIATE,
                )
            ],
        )
    ]

    gaps = await analyzer.analyze([role], ["backend"], diagnostics)

    assert len(gaps) == 1
    assert gaps[0].gap_type == TeamGapType.SKILL_ABSENCE
    assert "Python" in gaps[0].message
    assert "INTERMEDIATE" in gaps[0].message
    assert gaps[0].available_from is None


@pytest.mark.asyncio
async def test_skill_absence_message_uses_category_label():
    analyzer = TeamGapAnalyzer()
    role = _role(skill_names=[], skill_category=SkillCategoryEnum.QA)

    gaps = await analyzer.analyze([role], ["backend"], [])

    assert gaps[0].gap_type == TeamGapType.SKILL_ABSENCE
    assert "QA" in gaps[0].message


@pytest.mark.asyncio
async def test_skill_absence_when_only_bench_matches_but_unfilled():
    # Skilled members who are all on bench → still treated as no fillable bench match
    # for the unfilled role path when skilled exists but allocated list is empty.
    analyzer = TeamGapAnalyzer()
    role = _role()
    diagnostics = [_member(1, "Ada", is_bench=True)]

    gaps = await analyzer.analyze([role], ["backend"], diagnostics)

    assert len(gaps) == 1
    assert gaps[0].gap_type == TeamGapType.SKILL_ABSENCE
    assert "No bench employee matches Backend requirements." in gaps[0].message


@pytest.mark.asyncio
async def test_availability_conflict_for_allocated_skilled_member():
    availability = AsyncMock()
    availability.compute_available_from.return_value = date(2026, 8, 1)
    analyzer = TeamGapAnalyzer(availability_date_service=availability)
    role = _role()
    diagnostics = [_member(5, "Grace", is_bench=False)]

    gaps = await analyzer.analyze([role], ["backend"], diagnostics)

    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.gap_type == TeamGapType.AVAILABILITY_CONFLICT
    assert gap.candidate_hint_name == "Grace"
    assert gap.available_from == date(2026, 8, 1)
    assert "Grace" in gap.message
    assert "2026-08-01" in gap.message
    availability.compute_available_from.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_availability_conflict_unknown_date_without_service():
    analyzer = TeamGapAnalyzer(availability_date_service=None)
    role = _role()
    diagnostics = [_member(5, "Grace", is_bench=False)]

    gaps = await analyzer.analyze([role], ["backend"], diagnostics)

    assert gaps[0].gap_type == TeamGapType.AVAILABILITY_CONFLICT
    assert "available from unknown" in gaps[0].message
    assert gaps[0].available_from is None


@pytest.mark.asyncio
async def test_analyze_empty_unfilled_returns_empty():
    analyzer = TeamGapAnalyzer()
    gaps = await analyzer.analyze([_role()], [], [])
    assert gaps == []
