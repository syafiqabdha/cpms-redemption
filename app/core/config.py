from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "CPMS Autonomous Parking Redemption Gateway"
    APP_ENV: str = "development"  # development, test, staging, production
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Security & Pepper (HMAC-SHA256 secret vault pepper)
    SECRET_PEPPER: str = "dev-secret-pepper-change-in-production"

    # CORS settings
    CORS_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"

    # Operating Window & Timezone (Singapore Time UTC+8, 12:00 PM - 3:00 PM)
    OPERATING_TIMEZONE: str = "Asia/Singapore"
    OPERATING_START_HOUR: int = 12
    OPERATING_START_MINUTE: int = 0
    OPERATING_END_HOUR: int = 15
    OPERATING_END_MINUTE: int = 0

    # Business Rules
    MIN_RECEIPT_SPEND: float = 30.00
    VOUCHER_EXPIRY_HOURS: int = 2

    # Database & Redis infrastructure
    DATABASE_URL: str = "postgresql+asyncpg://cpms_user:cpms_pass@localhost:5432/cpms_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


settings = Settings()
