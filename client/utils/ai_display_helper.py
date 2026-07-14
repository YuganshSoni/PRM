import textwrap

from client.schemas.ai import RiskSummaryResponse, SkillMatchResponse


class AiDisplayHelper:
    SKILL_MATCH_DISCLAIMER = (
        "Note: Suggestions are AI-generated. Verify before confirming."
    )
    ASSISTANT_DISCLAIMER = (
        "Note: These are AI-generated suggestions. Always verify availability "
        "and skills with the employee before allocating."
    )
    RISK_DISCLAIMER = (
        "This summary is AI-generated from milestone and timesheet data."
    )

    @staticmethod
    def render_searching_message() -> None:
        print("Searching... (AI matching in progress)")

    @staticmethod
    def render_skill_match_results(
        response: SkillMatchResponse,
        *,
        disclaimer: str | None = None,
    ) -> None:
        print()
        if response.weekly_hours_requested is not None:
            print(
                f"AI-MATCHED RESULTS  "
                f"(for: {response.weekly_hours_requested} hrs/week)"
            )
        else:
            print("AI-MATCHED RESULTS")
        print("-" * 62)

        for item in response.items:
            availability = AiDisplayHelper._format_availability(item)
            print(f"{item.rank}.  {item.resource_name}")
            wrapped_reason = textwrap.fill(
                item.reason,
                width=58,
                initial_indent="    ",
                subsequent_indent="    ",
            )
            print(wrapped_reason)
            if availability:
                print(f"    {availability}")
            if item.suggested_utilisation_percent is not None:
                print(
                    f"    Suggested allocation: "
                    f"{item.suggested_utilisation_percent}%"
                )
            print()

        print("-" * 62)
        print(disclaimer or AiDisplayHelper.SKILL_MATCH_DISCLAIMER)
        print()

    @staticmethod
    def render_empty_skill_match(
        response: SkillMatchResponse,
        *,
        default_message: str = "No employees with enough free capacity.",
    ) -> None:
        message = response.message or default_message
        print()
        print(message)
        if not response.llm_invoked:
            if response.requirement_parse_invoked and message and "Could not identify" in message:
                print("(Requirement was too vague to search.)")
            elif response.requirement_parse_invoked:
                print("(No ranking was performed.)")
            else:
                print("(No AI call was made — no qualifying candidates.)")
        print()

    @staticmethod
    def render_risk_summary(response: RiskSummaryResponse) -> None:
        print()
        title = f"── AI Risk Summary — {response.project_name} "
        print(title + "─" * max(1, 62 - len(title)))
        print()
        wrapped = textwrap.fill(
            response.summary,
            width=62,
            break_long_words=False,
            break_on_hyphens=False,
        )
        print(wrapped)
        print()
        print(f"  Note: {response.disclaimer or AiDisplayHelper.RISK_DISCLAIMER}")
        print()

    @staticmethod
    def _format_availability(item) -> str:
        if item.free_hours_per_week is not None:
            return f"{item.free_hours_per_week:.0f} hrs free/week"
        return ""
