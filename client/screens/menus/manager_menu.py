from client.screens.menus.base_menu import BaseMenuScreen


class ManagerMenu(BaseMenuScreen):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__("MANAGER", *args, **kwargs)
