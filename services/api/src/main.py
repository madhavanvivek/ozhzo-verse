import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.router import api_v1_router
from src.core.config import settings
from src.core.exceptions import BaseDomainException
from src.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Initializing Ozhzo Verse Backend Service...")
    # Production secret key sanity check
    if settings.ENVIRONMENT == "production" and "development" in settings.JWT_SECRET_KEY:
        logger.critical("FATAL SECURITY RISK: Default development JWT secret key detected in production environment!")
    yield
    logger.info("Shutting down Ozhzo Verse Backend Service...")


app = FastAPI(
    title="Ozhzo Verse API",
    description="The Digital Operating System for Homes — Core Backend Service",
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# CORS Middleware (Strict Origin Validation with Development Flexibility)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


# Security Headers & Correlation Middleware
@app.middleware("http")
async def security_and_correlation_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = (time.perf_counter() - start_time) * 1000
    
    # Traceability Headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

    # OWASP Recommended Security Response Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({process_time:.2f}ms)",
        extra={"correlation_id": request_id}
    )
    return response


# Global Domain Exception Handler
@app.exception_handler(BaseDomainException)
async def domain_exception_handler(request: Request, exc: BaseDomainException):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "correlation_id": request_id,
            },
        },
    )


# Mount API v1
app.include_router(api_v1_router, prefix="/api/v1")
