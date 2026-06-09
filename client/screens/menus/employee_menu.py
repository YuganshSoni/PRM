from client.screens.menus.base_menu import BaseMenuScreen


class EmployeeMenu(BaseMenuScreen):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__("EMPLOYEE", *args, **kwargs)
