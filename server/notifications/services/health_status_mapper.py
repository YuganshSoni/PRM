from server.models.enums import HealthStatus


class HealthStatusMapper:
    _MAP = {
        HealthStatus.ON_TRACK: "Green",
        HealthStatus.ATTENTION: "Amber",
        HealthStatus.AT_RISK: "Red",
    }

    @classmethod
    def to_traffic_light(cls, status: HealthStatus | str) -> str:
        if isinstance(status, str):
            status = HealthStatus(status)
        return cls._MAP.get(status, status.value)
