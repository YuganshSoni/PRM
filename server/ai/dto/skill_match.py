from dataclasses import dataclass


@dataclass(frozen=True)
class SkillMatchCandidateDTO:
    resource_id: int
    resource_name: str
    utilisation_percent: int
    free_hours_per_week: float
    skills: list[str]
    recent_activity_tags: list[str]

    def to_prompt_line(self) -> str:
        skills_text = ", ".join(self.skills) if self.skills else "none listed"
        tags_text = (
            ", ".join(self.recent_activity_tags)
            if self.recent_activity_tags
            else "none"
        )
        return (
            f"Name: {self.resource_name}; "
            f"Utilisation: {self.utilisation_percent}%; "
            f"Free hours/week: {self.free_hours_per_week:.1f}; "
            f"Skills: {skills_text}; "
            f"Recent activity tags: {tags_text}"
        )
