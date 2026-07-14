class ApiKeyMasker:
    MASK = "****************************"

    @staticmethod
    def mask(api_key: str) -> str:
        return ApiKeyMasker.MASK if api_key.strip() else ""
