from server.models.enums import HealthStatus


class HealthDisplayHelper:
    _ICONS = {
        HealthStatus.ON_TRACK: "🟢",
        HealthStatus.ATTENTION: "🟡",
        HealthStatus.AT_RISK: "🔴",
    }

    _LABELS = {
        HealthStatus.ON_TRACK: "ON TRACK",
        HealthStatus.ATTENTION: "ATTENTION",
        HealthStatus.AT_RISK: "AT RISK",
    }

    @classmethod
    def format(cls, health_status: str | None) -> str:
        if health_status is None:
            return "— Pending"
        status = HealthStatus(health_status)
        icon = cls._ICONS.get(status, "")
        label = cls._LABELS.get(status, health_status.replace("_", " "))
        return f"{icon} {label}".strip()

    @classmethod
    def format_short(cls, health_status: str | None) -> str:
        if health_status is None:
            return "—"
        status = HealthStatus(health_status)
        icon = cls._ICONS.get(status, "")
        label = cls._LABELS.get(status, health_status.replace("_", " "))
        return f"{icon} {label}".strip()
