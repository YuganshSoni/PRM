from typing import Any


class NavigationStack:
    def __init__(self) -> None:
        self._screens: list[Any] = []

    def push(self, screen: Any) -> None:
        self._screens.append(screen)

    def pop(self) -> Any | None:
        if not self._screens:
            return None
        return self._screens.pop()

    def peek(self) -> Any | None:
        if not self._screens:
            return None
        return self._screens[-1]

    def clear(self) -> None:
        self._screens.clear()
