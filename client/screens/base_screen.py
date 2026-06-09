from abc import ABC, abstractmethod

from client.api.httpx_client import HttpxClient
from client.navigation import NavigationStack
from client.screens.screen_result import ScreenResult
from client.session import SessionManager
from client.ui.console_reader import ConsoleReader
from client.ui.console_renderer import ConsoleRenderer


class BaseScreen(ABC):
    def __init__(
        self,
        client: HttpxClient,
        session_manager: SessionManager,
        navigation: NavigationStack,
        renderer: ConsoleRenderer,
        reader: ConsoleReader,
    ) -> None:
        self._client = client
        self._session_manager = session_manager
        self._navigation = navigation
        self._renderer = renderer
        self._reader = reader

    @abstractmethod
    async def run(self) -> ScreenResult:
        ...

    def go_back(self) -> None:
        self._navigation.pop()
