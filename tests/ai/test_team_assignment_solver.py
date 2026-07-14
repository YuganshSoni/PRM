from server.ai.dto.team_build import (
    RoleRequirementDTO,
    SkillProficiencyDTO,
    TeamBuildCandidateDTO,
)
from server.ai.services.team_assignment_solver import TeamAssignmentSolver
from server.models.enums import ProficiencyLevel, SkillCategoryEnum


def _skill(name: str, level: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE):
    return SkillProficiencyDTO(
        skill_name=name,
        category=SkillCategoryEnum.BACKEND,
        proficiency=level,
    )


def _role(key: str, skill: str) -> RoleRequirementDTO:
    return RoleRequirementDTO(
        role_key=key,
        role_title=key,
        skill_names=[skill],
        skill_category=None,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
    )


def _candidate(resource_id: int, name: str, skills: list[str]) -> TeamBuildCandidateDTO:
    return TeamBuildCandidateDTO(
        resource_id=resource_id,
        resource_name=name,
        skills=[_skill(s) for s in skills],
        recent_activity_tags=[],
    )


def test_solve_empty_roles_returns_empty():
    solver = TeamAssignmentSolver()
    assignments, unfilled = solver.solve([], [_candidate(1, "A", ["Python"])])
    assert assignments == []
    assert unfilled == []


def test_solve_assigns_best_unique_candidates():
    solver = TeamAssignmentSolver()
    roles = [_role("backend", "Python"), _role("data", "SQL")]
    candidates = [
        _candidate(1, "Ada", ["Python", "SQL"]),
        _candidate(2, "Grace", ["SQL"]),
        _candidate(3, "Alan", ["Python"]),
    ]

    assignments, unfilled = solver.solve(roles, candidates)

    assert unfilled == []
    assert len(assignments) == 2
    assigned_ids = {a.resource_id for a in assignments}
    assert len(assigned_ids) == 2
    by_key = {a.role_key: a for a in assignments}
    assert by_key["backend"].resource_id in {1, 3}
    assert by_key["data"].resource_id in {1, 2}
    assert by_key["backend"].resource_id != by_key["data"].resource_id


def test_solve_marks_all_unfilled_when_complete_assignment_impossible():
    # Backtracker only records solutions that fill every role in order;
    # a partial fill does not become best_assignments.
    solver = TeamAssignmentSolver()
    roles = [_role("backend", "Python"), _role("frontend", "React")]
    candidates = [_candidate(1, "Ada", ["Python"])]

    assignments, unfilled = solver.solve(roles, candidates)

    assert assignments == []
    assert unfilled == ["backend", "frontend"]


def test_solve_cannot_reuse_same_candidate_so_second_role_blocks_solution():
    solver = TeamAssignmentSolver()
    roles = [_role("r1", "Python"), _role("r2", "Python")]
    candidates = [_candidate(1, "Ada", ["Python"])]

    assignments, unfilled = solver.solve(roles, candidates)

    assert assignments == []
    assert unfilled == ["r1", "r2"]


def test_solve_two_matching_candidates_fills_duplicate_skill_roles():
    solver = TeamAssignmentSolver()
    roles = [_role("r1", "Python"), _role("r2", "Python")]
    candidates = [
        _candidate(1, "Ada", ["Python"]),
        _candidate(2, "Grace", ["Python"]),
    ]

    assignments, unfilled = solver.solve(roles, candidates)

    assert unfilled == []
    assert len(assignments) == 2
    assert {a.resource_id for a in assignments} == {1, 2}


def test_solve_prefers_higher_total_score():
    solver = TeamAssignmentSolver()
    roles = [
        RoleRequirementDTO(
            role_key="lead",
            role_title="Lead",
            skill_names=["Python"],
            skill_category=SkillCategoryEnum.BACKEND,
            min_proficiency=ProficiencyLevel.INTERMEDIATE,
        )
    ]
    multi_skill = TeamBuildCandidateDTO(
        resource_id=1,
        resource_name="Ada",
        skills=[
            _skill("Python"),
            SkillProficiencyDTO(
                skill_name="Extra",
                category=SkillCategoryEnum.BACKEND,
                proficiency=ProficiencyLevel.INTERMEDIATE,
            ),
        ],
        recent_activity_tags=[],
    )
    single = _candidate(2, "Grace", ["Python"])

    assignments, unfilled = solver.solve(roles, [single, multi_skill])

    assert unfilled == []
    assert assignments[0].resource_id == 1
    assert assignments[0].match_score > 10


def test_solve_all_unfilled_when_no_candidates():
    solver = TeamAssignmentSolver()
    roles = [_role("backend", "Python")]

    assignments, unfilled = solver.solve(roles, [])

    assert assignments == []
    assert unfilled == ["backend"]
