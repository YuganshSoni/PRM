from getpass import getpass


class ConsoleReader:
    def read_line(self, prompt: str) -> str:
        return input(prompt).strip()

    def read_option(self, prompt: str) -> str:
        return input(prompt).strip()

    def read_password(self, prompt: str) -> str:
        return getpass(prompt).strip()
