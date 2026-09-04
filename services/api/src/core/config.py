import os
from typing import List
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # API
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:3001,"
        "http://127.0.0.1:3001,"
        "http://localhost:8000,"
        "http://127.0.0.1:8000,"
        "https://ozhzo.com,"
        "https://www.ozhzo.com,"
        "https://ozhzo-web.onrender.com,"
        "https://ozhzo-verse.onrender.com"
    )

    # Security
    JWT_SECRET_KEY: str = "default_development_secret_key_change_in_prod_32char"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP: bool = True
    SUPER_ADMIN_EMAIL: str = os.getenv("SUPER_ADMIN_EMAIL", os.getenv("DEMO_SUPER_ADMIN_EMAIL", "superadmin@ozhzo.com"))
    SUPER_ADMIN_PASSWORD: str = os.getenv("SUPER_ADMIN_PASSWORD", os.getenv("DEMO_SUPER_ADMIN_PASSWORD", ""))
    DEMO_SUPER_ADMIN_EMAIL: str = os.getenv("DEMO_SUPER_ADMIN_EMAIL", os.getenv("SUPER_ADMIN_EMAIL", "superadmin@ozhzo.com"))
    DEMO_SUPER_ADMIN_PASSWORD: str = os.getenv("DEMO_SUPER_ADMIN_PASSWORD", os.getenv("SUPER_ADMIN_PASSWORD", ""))
    FORCE_SUPER_ADMIN_PASSWORD_RESET: bool = True
    DEMO_OTP_ENABLED: bool = True
    DEMO_OTP_CODE: str = "123456"

    # Transactional Email (SMTP / Resend)
    EMAIL_PROVIDER: str = "smtp"
    EMAIL_SENDER_ADDRESS: str = "no-reply@ozhzoverse.com"
    EMAIL_SENDER_NAME: str = "Ozhzo Verse"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    RESEND_API_KEY: str | None = None

    # PostgreSQL Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_NAME: str = "ozhzo_verse"
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ozhzo_verse"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/ozhzo_verse"
    )

    # Redis Cache
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Payment Gateway Configuration (Stage 2.2C)
    PAYMENT_GATEWAY_PROVIDER: str = "MOCK_GATEWAY"  # MOCK_GATEWAY, RAZORPAY, STRIPE
    PAYMENT_GATEWAY_ENVIRONMENT: str = "test"  # development, test, production
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None
    STRIPE_PUBLISHABLE_KEY: str | None = None
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
        dev_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        for dev in dev_origins:
            if dev not in origins:
                origins.append(dev)
        return origins


settings = Settings()
