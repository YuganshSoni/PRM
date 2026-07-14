import pytest

from server.models.enums import HealthStatus
from server.notifications.services.health_status_mapper import HealthStatusMapper


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (HealthStatus.ON_TRACK, "Green"),
        (HealthStatus.ATTENTION, "Amber"),
        (HealthStatus.AT_RISK, "Red"),
        ("ON_TRACK", "Green"),
        ("ATTENTION", "Amber"),
        ("AT_RISK", "Red"),
    ],
)
def test_to_traffic_light_known_statuses(status, expected):
    assert HealthStatusMapper.to_traffic_light(status) == expected


def test_to_traffic_light_falls_back_to_enum_value_for_unmapped():
    original = HealthStatusMapper._MAP
    try:
        HealthStatusMapper._MAP = {}
        assert HealthStatusMapper.to_traffic_light(HealthStatus.ON_TRACK) == "ON_TRACK"
    finally:
        HealthStatusMapper._MAP = original


def test_to_traffic_light_rejects_invalid_string():
    with pytest.raises(ValueError):
        HealthStatusMapper.to_traffic_light("NOT_A_STATUS")
