class ConsoleRenderer:
    def render_banner(self, title: str, subtitle: str | None = None) -> None:
        print("╔══════════════════════════════════════════════╗")
        print(f"║    {title:<40} ║")
        if subtitle:
            print(f"║    {subtitle:<40} ║")
        print("╚══════════════════════════════════════════════╝")
        print()

    def render_box_title(self, title: str, subtitle: str | None = None) -> None:
        print("╔══════════════════════════════════════════════╗")
        print(f"║    {title:<40} ║")
        if subtitle:
            print(f"║    {subtitle:<40} ║")
        print("╚══════════════════════════════════════════════╝")
        print()

    def render_message(self, message: str) -> None:
        print(message)
        print()

    def render_error(self, message: str) -> None:
        print(f"Error: {message}")
        print()

    def render_divider(self) -> None:
        print("──────────────────────────────────────────────")
