from client.screens.menus.base_menu import BaseMenuScreen


class AdminMenu(BaseMenuScreen):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__("ADMIN", *args, **kwargs)
