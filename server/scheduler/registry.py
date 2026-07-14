from server.scheduler.scheduler_manager import SchedulerManager

_manager: SchedulerManager | None = None


def set_scheduler_manager(manager: SchedulerManager | None) -> None:
    global _manager
    _manager = manager


def get_scheduler_manager() -> SchedulerManager | None:
    return _manager
