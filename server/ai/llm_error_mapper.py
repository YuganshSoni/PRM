class LlmErrorMapper:
    @staticmethod
    def user_message(exc: Exception, operation: str) -> str:
        text = f"{type(exc).__name__}: {exc}".lower()
        if "api key not valid" in text or "api_key_invalid" in text:
            return (
                "LLM API key is invalid. Create a new key at Google AI Studio "
                "(https://aistudio.google.com/apikey) and update .env or "
                "Admin → System Configuration."
            )
        if "quota" in text or "resourceexhausted" in text or "429" in text:
            return (
                "LLM quota exceeded. Wait and retry, change GEMINI_MODEL in .env, "
                "or switch to GROQ in System Configuration."
            )
        if "not found" in text and "model" in text:
            return (
                "LLM model not found or unavailable. Check GEMINI_MODEL or GROQ_MODEL "
                "in .env."
            )
        return f"AI {operation} failed. Check server logs for details."

    @staticmethod
    def log_summary(exc: Exception) -> str:
        return f"{type(exc).__name__}: {exc}"
