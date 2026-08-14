from typing import Generic, Optional, TypeVar, Any, Dict
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponseMeta(BaseModel):
    page: Optional[int] = None
    limit: Optional[int] = None
    total: Optional[int] = None
    has_next: Optional[bool] = None


class ApiSuccessResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    success: bool = True
    data: T
    meta: Optional[ApiResponseMeta] = None


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiErrorDetail
