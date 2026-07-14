from enum import StrEnum


class ScreenResult(StrEnum):
    EXIT = "exit"
    START = "start"
    LOGIN = "login"
    CHANGE_PASSWORD = "change_password"
    MENU = "menu"
    LOGOUT = "logout"
    RETRY = "retry"
    BACK = "back"
    GO_ALLOCATE = "go_allocate"
