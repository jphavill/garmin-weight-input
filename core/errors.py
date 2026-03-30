class GarminAuthError(RuntimeError):
    pass


class GarminUpdateError(RuntimeError):
    def __init__(self, message: str, status_code: int, response_body: str, activity_id: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.activity_id = activity_id


class ActivityNotFoundError(RuntimeError):
    def __init__(self, message: str, activity_id: int | None = None):
        super().__init__(message)
        self.activity_id = activity_id


class ActivityTooOldError(RuntimeError):
    def __init__(self, details: dict):
        super().__init__("Latest activity is older than 8 hours")
        self.details = details


class ActivityTypeMismatchError(RuntimeError):
    def __init__(self, details: dict):
        super().__init__("Latest activity is not hiking")
        self.details = details


class GarminUpstreamError(GarminUpdateError):
    pass


class ResourceNotFoundError(ActivityNotFoundError):
    pass


class InvalidActivityTypeError(ActivityTypeMismatchError):
    pass


class InvalidGarminPayloadError(RuntimeError):
    pass
