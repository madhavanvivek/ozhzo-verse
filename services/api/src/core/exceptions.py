from typing import Any, Dict, Optional


class BaseDomainException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_DOMAIN_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundException(BaseDomainException):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with ID '{entity_id}' was not found.",
            code=f"{entity_name.upper()}_NOT_FOUND",
            status_code=404,
            details={"entity": entity_name, "id": str(entity_id)},
        )


class PermissionDeniedException(BaseDomainException):
    def __init__(self, permission: str):
        super().__init__(
            message=f"You do not have permission '{permission}' to perform this action.",
            code="PERMISSION_DENIED",
            status_code=403,
            details={"required_permission": permission},
        )


class InvalidCredentialsException(BaseDomainException):
    def __init__(self):
        super().__init__(
            message="Invalid email or password.",
            code="INVALID_CREDENTIALS",
            status_code=401,
        )


class TierLimitExceededException(BaseDomainException):
    def __init__(self, resource: str, limit: int):
        super().__init__(
            message=f"Free tier limit of {limit} {resource} reached. Please upgrade to Premium.",
            code=f"TIER_LIMIT_{resource.upper()}_EXCEEDED",
            status_code=402,
            details={"resource": resource, "limit": limit},
        )


class MobileVerificationRequiredException(BaseDomainException):
    def __init__(self, message: str = "Mobile number verification is required before creating a Home."):
        super().__init__(
            message=message,
            code="MOBILE_VERIFICATION_REQUIRED",
            status_code=403,
            details={"action": "CREATE_HOME", "verification_required": "mobile"},
        )
