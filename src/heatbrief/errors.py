class HeatBriefError(Exception):
    """An actionable domain failure safe to display to a client."""

    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code = code
        self.status = status
