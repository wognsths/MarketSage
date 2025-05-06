class MissingAPIKeyError(Exception):
    """Exception for missing API key(s)"""

    def __init__(self, missing_keys: list[str]):
        message = f"Please check your API keys. Missing keys: {', '.join(missing_keys)}"
        super().__init__(message)
        self.missing_keys = missing_keys