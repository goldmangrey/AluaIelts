from http import HTTPStatus


class AluaError(Exception):
    def __init__(self, message: str, code: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(AluaError):
    def __init__(self, message: str, code: str = "not_found") -> None:
        super().__init__(message, code, HTTPStatus.NOT_FOUND)


class ValidationError(AluaError):
    def __init__(self, message: str, code: str = "validation_error") -> None:
        super().__init__(message, code, HTTPStatus.UNPROCESSABLE_ENTITY)


class UnauthorizedError(AluaError):
    def __init__(self, message: str, code: str = "unauthorized") -> None:
        super().__init__(message, code, HTTPStatus.UNAUTHORIZED)


class ForbiddenError(AluaError):
    def __init__(self, message: str, code: str = "forbidden") -> None:
        super().__init__(message, code, HTTPStatus.FORBIDDEN)


class ConflictError(AluaError):
    def __init__(self, message: str, code: str = "conflict") -> None:
        super().__init__(message, code, HTTPStatus.CONFLICT)


class ExternalServiceError(AluaError):
    def __init__(self, message: str, code: str = "external_service_error") -> None:
        super().__init__(message, code, HTTPStatus.SERVICE_UNAVAILABLE)
