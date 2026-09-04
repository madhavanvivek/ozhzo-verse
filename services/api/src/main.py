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

    # Safe and idempotent database schema synchronization
    try:
        from src.infrastructure.database.models import Base
        from src.infrastructure.database.session import engine
        from sqlalchemy import text
        async with engine.begin() as conn:
            # 1. Create all registered tables if they do not exist
            await conn.run_sync(Base.metadata.create_all)

            # 2. Idempotently ensure domain columns exist on legacy tables
            columns_to_ensure = [
                ("inventory_items", "brand", "VARCHAR"),
                ("inventory_items", "model_number", "VARCHAR"),
                ("inventory_items", "serial_number", "VARCHAR"),
                ("inventory_items", "barcode", "VARCHAR"),
                ("inventory_items", "qr_code_identifier", "VARCHAR"),
                ("inventory_items", "purchase_date", "DATE"),
                ("inventory_items", "purchase_price", "NUMERIC(12, 2)"),
                ("inventory_items", "purchase_store", "VARCHAR"),
                ("inventory_items", "warranty_expiry_date", "DATE"),
                ("inventory_items", "warranty_notes", "VARCHAR"),
                ("inventory_items", "photo_url", "VARCHAR"),
                ("inventory_items", "receipt_url", "VARCHAR"),
                ("inventory_items", "manual_url", "VARCHAR"),
                ("inventory_items", "last_serviced_at", "DATE"),
                ("inventory_items", "next_service_due_at", "DATE"),
                ("inventory_items", "service_notes", "VARCHAR"),
                ("homes", "status", "VARCHAR DEFAULT 'ACTIVE'"),
                ("homes", "public_home_id", "VARCHAR(16)"),
                ("homes", "home_qr_token", "VARCHAR(128)"),
                ("homes", "home_qr_status", "VARCHAR(32) DEFAULT 'ACTIVE'"),
                ("homes", "home_qr_version", "INTEGER DEFAULT 1"),
                ("homes", "home_qr_created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("homes", "home_qr_revoked_at", "TIMESTAMP WITH TIME ZONE"),
                ("users", "is_super_admin", "BOOLEAN DEFAULT FALSE"),
                ("users", "system_role", "VARCHAR DEFAULT 'USER'"),
                ("users", "mobile_verified", "BOOLEAN DEFAULT FALSE"),
                ("invitations", "invitation_code", "VARCHAR(32)"),
                ("invitations", "revoked_at", "TIMESTAMP WITH TIME ZONE"),
                ("tasks", "bill_id", "UUID"),
                ("notifications", "priority", "VARCHAR(32) DEFAULT 'NORMAL'"),
                ("notifications", "action_type", "VARCHAR(64)"),
                ("notifications", "action_url", "VARCHAR(255)"),
                ("notifications", "action_label", "VARCHAR(64)"),
                ("notifications", "dedup_key", "VARCHAR(128)")
            ]
            for table, col, col_type in columns_to_ensure:
                try:
                    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type};"))
                except Exception:
                    pass

            # 3. Idempotently relax legacy NOT NULL constraints on evolved tables
            relax_constraints = [
                "ALTER TABLE bills ALTER COLUMN category DROP NOT NULL;",
                "ALTER TABLE bills ALTER COLUMN amount DROP NOT NULL;",
                "ALTER TABLE bills ALTER COLUMN recurrence_interval DROP NOT NULL;",
                "ALTER TABLE notifications ALTER COLUMN home_id DROP NOT NULL;"
            ]
            for stmt in relax_constraints:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass

            # 4. Idempotently ensure composite performance indexes
            indexes_to_ensure = [
                "CREATE INDEX IF NOT EXISTS idx_tasks_home_status_due ON tasks (home_id, status, due_date);",
                "CREATE INDEX IF NOT EXISTS idx_bills_home_status_due ON bills (home_id, status, due_date);",
                "CREATE INDEX IF NOT EXISTS idx_sub_audit_time ON subscription_audit_logs (created_at DESC);",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_homes_public_home_id ON homes (public_home_id) WHERE public_home_id IS NOT NULL;",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_homes_qr_token ON homes (home_qr_token) WHERE home_qr_token IS NOT NULL;",
                "CREATE INDEX IF NOT EXISTS idx_notifications_user_prio_read ON notifications (user_id, priority, is_read, created_at);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_dedup ON notifications (dedup_key);",
                "CREATE INDEX IF NOT EXISTS idx_ai_usage_home_time ON ai_usage_records (home_id, created_at);",
                "CREATE INDEX IF NOT EXISTS idx_bg_jobs_status_next_run ON background_jobs (status, next_run_at);",
                "CREATE INDEX IF NOT EXISTS idx_hh_mem_home_status ON household_memories (home_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_hh_mem_home_cat ON household_memories (home_id, category);",
                "CREATE INDEX IF NOT EXISTS idx_auto_exec_home_time ON automation_executions (home_id, created_at);"
            ]
            for idx_stmt in indexes_to_ensure:
                try:
                    await conn.execute(text(idx_stmt))
                except Exception:
                    pass


            # 5. Backfill existing homes missing public_home_id or home_qr_token
            try:
                import secrets
                res = await conn.execute(text("SELECT id FROM homes WHERE public_home_id IS NULL OR home_qr_token IS NULL;"))
                unfilled_homes = res.fetchall()
                for (h_id,) in unfilled_homes:
                    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
                    h_code = "OZH-" + "".join(secrets.choice(chars) for _ in range(6))
                    qr_tok = secrets.token_urlsafe(32)
                    await conn.execute(text(
                        f"UPDATE homes SET public_home_id = COALESCE(public_home_id, '{h_code}'), "
                        f"home_qr_token = COALESCE(home_qr_token, '{qr_tok}'), "
                        f"home_qr_status = COALESCE(home_qr_status, 'ACTIVE'), "
                        f"home_qr_version = COALESCE(home_qr_version, 1) WHERE id = '{h_id}';"
                    ))
            except Exception as bf_err:
                logger.warning(f"Home identity backfill notice: {bf_err}")
        logger.info("Database schema synchronization completed successfully.")
    except Exception as e:
        logger.warning(f"Database schema sync warning: {e}")

    # Safe and idempotent Super Admin initialization
    if settings.ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP:
        try:
            from src.infrastructure.database.session import AsyncSessionLocal
            from src.core.bootstrap import seed_demo_super_admin
            async with AsyncSessionLocal() as db:
                await seed_demo_super_admin(db)
        except Exception as e:
            logger.warning(f"Super Admin bootstrap encountered an issue during startup: {e}")

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


# Unhandled Global Exception Handler
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    logger.exception(
        f"Unhandled exception during {request.method} {request.url.path}: {exc}",
        extra={"correlation_id": request_id}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal error occurred. Our engineers have been alerted.",
                "details": str(exc) if (settings.DEBUG or settings.ENVIRONMENT != "production") else None,
                "correlation_id": request_id,
            },
        },
    )


# Mount API v1
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "ozhzo-verse-api", "version": "1.0.0"}

