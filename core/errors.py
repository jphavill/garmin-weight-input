class GarminAuthError(RuntimeError):
    pass


class GarminUpstreamError(RuntimeError):
    def __init__(self, message: str, status_code: int, response_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ResourceNotFoundError(RuntimeError):
    pass


class InvalidActivityTypeError(RuntimeError):
    def __init__(self, details: dict):
        super().__init__("Latest activity is not hiking")
        self.details = details


class InvalidGarminPayloadError(RuntimeError):
    pass
