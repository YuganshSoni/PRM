from dataclasses import dataclass


@dataclass
class AiFlowContext:
    requirement: str | None = None
    project_id: int | None = None
    selected_resource_id: int | None = None
    suggested_utilisation_percent: int | None = None
