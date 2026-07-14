from client.api.httpx_client import HttpxClient
from client.context.ai_context_store import AiContextStore
from client.navigation import NavigationStack
from client.screens.base_screen import BaseScreen
from client.screens.menus.admin_menu import AdminMenu
from client.screens.menus.resource_menu import ResourceMenu
from client.screens.menus.manager_menu import ManagerMenu
from client.session import SessionManager
from client.ui.console_reader import ConsoleReader
from client.ui.console_renderer import ConsoleRenderer
from server.models.enums import UserRole


class ScreenFactory:
    def __init__(
        self,
        client: HttpxClient,
        session_manager: SessionManager,
        navigation: NavigationStack,
        renderer: ConsoleRenderer,
        reader: ConsoleReader,
        ai_context_store: AiContextStore,
    ) -> None:
        self._client = client
        self._session_manager = session_manager
        self._navigation = navigation
        self._renderer = renderer
        self._reader = reader
        self._ai_context_store = ai_context_store

    def create_menu_for_role(self, role: UserRole) -> BaseScreen:
        common_args = (
            self._client,
            self._session_manager,
            self._navigation,
            self._renderer,
            self._reader,
        )
        match role:
            case UserRole.ADMIN:
                return AdminMenu(*common_args)
            case UserRole.MANAGER:
                return ManagerMenu(
                    *common_args,
                    ai_context_store=self._ai_context_store,
                )
            case UserRole.RESOURCE:
                return ResourceMenu(*common_args)
            case _:
                raise ValueError(f"Unsupported role: {role}")
