import textwrap

from client.schemas.team_build import TeamBuildResponse


class TeamBuildDisplayHelper:
    @staticmethod
    def render_searching_message() -> None:
        print("Building team... (AI parsing and matching in progress)")

    @staticmethod
    def render_results(response: TeamBuildResponse) -> None:
        print()
        print("PARSED ROLES")
        print("-" * 62)
        for role in response.parsed_roles:
            skills = ", ".join(role.skill_names) or (role.skill_category or "ANY")
            print(
                f"  {role.role_title}: {skills} "
                f"({role.min_proficiency})"
            )
        print()

        if response.matches:
            print("MATCHED TEAM")
            print("-" * 62)
            for match in response.matches:
                print(f"  {match.role_title} -> {match.resource_name}")
                wrapped = textwrap.fill(
                    match.reason,
                    width=56,
                    initial_indent="    ",
                    subsequent_indent="    ",
                )
                print(wrapped)
                print()

        if response.gaps:
            print("GAPS")
            print("-" * 62)
            for gap in response.gaps:
                print(f"  {gap.role_title} [{gap.gap_type}]")
                wrapped = textwrap.fill(
                    gap.message,
                    width=56,
                    initial_indent="    ",
                    subsequent_indent="    ",
                )
                print(wrapped)
                if gap.available_from is not None:
                    print(f"    Available from: {gap.available_from.isoformat()}")
                print()

        print("-" * 62)
        print(f"Note: {response.disclaimer}")
        print()
