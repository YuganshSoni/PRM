from client.exceptions import ApiRequestError


class AiErrorMapper:
    _MESSAGES: dict[str, str] = {
        "LlmNotConfiguredError": (
            "AI is not configured. Ask Admin to set the LLM API key "
            "in System Configuration."
        ),
        "LlmInvocationError": (
            "AI service temporarily unavailable. Try again later."
        ),
        "ProjectNotFoundError": "Project not found or not owned by you.",
        "ManagerProfileNotFoundError": "Manager profile not found.",
        "EmployeeNotAllocatableError": (
            "Employee is not on your team or is inactive."
        ),
    }

    @classmethod
    def message_for(cls, exc: ApiRequestError) -> str:
        if exc.code == "LlmInvocationError" and exc.message:
            return exc.message
        return cls._MESSAGES.get(exc.code, exc.message)
