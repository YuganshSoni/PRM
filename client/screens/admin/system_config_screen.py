from client.exceptions import ApiRequestError, NetworkError
from client.screens.base_screen import BaseScreen
from client.screens.screen_result import ScreenResult
from server.models.enums import LlmProvider


class SystemConfigScreen(BaseScreen):
    _PROVIDER_LABELS = {
        LlmProvider.GEMINI: "Google Gemini",
        LlmProvider.GROQ: "Groq",
    }

    async def run(self) -> ScreenResult:
        while True:
            try:
                config = await self._client.get_config()
            except NetworkError as exc:
                self._renderer.render_error(exc.message)
                return ScreenResult.RETRY
            except ApiRequestError as exc:
                self._renderer.render_error(exc.message)
                return ScreenResult.RETRY

            self._renderer.render_box_title("SYSTEM CONFIGURATION")
            print()
            print("Current Settings:")
            provider_label = self._PROVIDER_LABELS.get(
                LlmProvider(config.llm_provider),
                config.llm_provider,
            )
            key_display = config.llm_api_key_masked or "(not set)"
            email_status = "Enabled" if config.email_enabled else "Disabled"
            smtp_password_display = config.smtp_password_masked or "(not set)"
            print(f"  LLM Provider        :  {provider_label}")
            print(f"  LLM API Key         :  {key_display}")
            print(f"  Scheduler Interval  :  {config.scheduler_interval_hours} hours")
            print(f"  Max Weekly Hours    :  {config.max_weekly_hours}")
            print(f"  Email Notifications :  {email_status}")
            print(f"  SMTP Host           :  {config.smtp_host or '(not set)'}")
            print(f"  SMTP Port           :  {config.smtp_port}")
            print(f"  SMTP Username       :  {config.smtp_username or '(not set)'}")
            print(f"  SMTP Password       :  {smtp_password_display}")
            print(f"  SMTP From Email     :  {config.smtp_from_email or '(not set)'}")
            print()
            print("─" * 46)
            print("1. Update LLM API Key")
            print("2. Change LLM Provider  (Gemini / Groq)")
            print("3. Update Scheduler Interval")
            print("4. Update Max Weekly Hours")
            print("5. Toggle Email Notifications")
            print("6. Update SMTP Settings")
            print("7. Back")
            print()

            option = self._reader.read_option("Enter option: ").strip()
            if option == "7":
                return ScreenResult.BACK

            result = await self._handle_option(option)
            if result == ScreenResult.RETRY:
                continue

    async def _handle_option(self, option: str) -> ScreenResult:
        match option:
            case "1":
                return await self._update_api_key()
            case "2":
                return await self._change_provider()
            case "3":
                return await self._update_scheduler_interval()
            case "4":
                return await self._update_max_weekly_hours()
            case "5":
                return await self._toggle_email()
            case "6":
                return await self._update_smtp_settings()
            case _:
                self._renderer.render_error("Invalid option. Please enter 1–7.")
                return ScreenResult.RETRY

    async def _update_api_key(self) -> ScreenResult:
        api_key = self._reader.read_password("New LLM API Key: ")
        if not api_key.strip():
            self._renderer.render_error("API key cannot be empty.")
            return ScreenResult.RETRY
        return await self._save_config(llm_api_key=api_key.strip())

    async def _change_provider(self) -> ScreenResult:
        print("(1) Gemini   (2) Groq")
        choice = self._reader.read_line("Enter choice: ").strip()
        match choice:
            case "1":
                provider = LlmProvider.GEMINI.value
            case "2":
                provider = LlmProvider.GROQ.value
            case _:
                self._renderer.render_error("Invalid choice. Enter 1 or 2.")
                return ScreenResult.RETRY
        return await self._save_config(llm_provider=provider)

    async def _update_scheduler_interval(self) -> ScreenResult:
        value = self._reader.read_line("Scheduler interval (hours): ")
        if not value.isdigit():
            self._renderer.render_error("Enter a valid number of hours.")
            return ScreenResult.RETRY
        return await self._save_config(scheduler_interval_hours=int(value))

    async def _update_max_weekly_hours(self) -> ScreenResult:
        value = self._reader.read_line("Max weekly hours: ")
        if not value.isdigit():
            self._renderer.render_error("Enter a valid number of hours.")
            return ScreenResult.RETRY
        return await self._save_config(max_weekly_hours=int(value))

    async def _toggle_email(self) -> ScreenResult:
        print("(1) Enable   (2) Disable")
        choice = self._reader.read_line("Enter choice: ").strip()
        match choice:
            case "1":
                return await self._save_config(email_enabled=True)
            case "2":
                return await self._save_config(email_enabled=False)
            case _:
                self._renderer.render_error("Invalid choice. Enter 1 or 2.")
                return ScreenResult.RETRY

    async def _update_smtp_settings(self) -> ScreenResult:
        host = self._reader.read_line("SMTP Host: ").strip()
        port_raw = self._reader.read_line("SMTP Port (587): ").strip()
        username = self._reader.read_line("SMTP Username: ").strip()
        password = self._reader.read_password("SMTP Password: ")
        from_email = self._reader.read_line("SMTP From Email: ").strip()

        fields: dict[str, str | int | bool] = {}
        if host:
            fields["smtp_host"] = host
        if port_raw:
            if not port_raw.isdigit():
                self._renderer.render_error("SMTP port must be a number.")
                return ScreenResult.RETRY
            fields["smtp_port"] = int(port_raw)
        if username:
            fields["smtp_username"] = username
        if password.strip():
            fields["smtp_password"] = password.strip()
        if from_email:
            fields["smtp_from_email"] = from_email

        if not fields:
            self._renderer.render_error("Enter at least one SMTP field to update.")
            return ScreenResult.RETRY

        return await self._save_config(**fields)

    async def _save_config(self, **fields: str | int | bool) -> ScreenResult:
        try:
            await self._client.update_config(**fields)
        except NetworkError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY
        except ApiRequestError as exc:
            self._renderer.render_error(exc.message)
            return ScreenResult.RETRY

        self._renderer.render_message("Settings updated. ✓")
        return ScreenResult.RETRY
