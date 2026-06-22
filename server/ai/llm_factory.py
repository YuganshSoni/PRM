from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from server.core.config import get_settings
from server.core.exceptions import LlmInvocationError
from server.models.enums import LlmProvider


class LLMFactory:
    DEFAULT_TIMEOUT_SEC = 30
    DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
    DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

    def create(self, provider: LlmProvider, api_key: str) -> BaseChatModel:
        settings = get_settings()
        gemini_model = settings.gemini_model.strip() or self.DEFAULT_GEMINI_MODEL
        groq_model = settings.groq_model.strip() or self.DEFAULT_GROQ_MODEL
        try:
            if provider == LlmProvider.GEMINI:
                return ChatGoogleGenerativeAI(
                    model=gemini_model,
                    google_api_key=api_key,
                    timeout=self.DEFAULT_TIMEOUT_SEC,
                )
            if provider == LlmProvider.GROQ:
                return ChatGroq(
                    model=groq_model,
                    api_key=api_key,
                    timeout=self.DEFAULT_TIMEOUT_SEC,
                )
            raise LlmInvocationError(f"Unsupported LLM provider: {provider}")
        except LlmInvocationError:
            raise
        except Exception as exc:
            raise LlmInvocationError(
                f"Failed to initialize LLM provider {provider.value}"
            ) from exc
