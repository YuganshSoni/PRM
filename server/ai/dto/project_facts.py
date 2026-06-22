from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProjectFactsMilestone:
    title: str
    due_date: str
    status: str
    is_overdue: bool


@dataclass(frozen=True)
class ProjectFactsAllocation:
    resource_name: str
    utilisation_percent: int


@dataclass(frozen=True)
class ProjectFactsDTO:
    project_id: int
    project_name: str
    project_status: str
    end_date: str
    health_status: str | None
    milestones: list[ProjectFactsMilestone] = field(default_factory=list)
    allocations: list[ProjectFactsAllocation] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    hours_notes: list[str] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        lines = [
            f"Project: {self.project_name} ({self.project_status})",
            f"End date: {self.end_date}",
        ]
        if self.health_status:
            lines.append(f"Health status: {self.health_status}")
        if self.risk_flags:
            lines.append("Risk flags:")
            lines.extend(f"- {flag}" for flag in self.risk_flags)
        if self.milestones:
            lines.append("Milestones:")
            for milestone in self.milestones:
                overdue = " OVERDUE" if milestone.is_overdue else ""
                lines.append(
                    f"- {milestone.title} due {milestone.due_date} "
                    f"({milestone.status}){overdue}"
                )
        if self.allocations:
            lines.append("Allocated resources:")
            for allocation in self.allocations:
                lines.append(
                    f"- {allocation.resource_name} at {allocation.utilisation_percent}%"
                )
        if self.hours_notes:
            lines.append("Recent hours:")
            lines.extend(f"- {note}" for note in self.hours_notes)
        return "\n".join(lines)
