"""Centralised settings (pydantic-settings, env-driven).

Override via .env file or environment variables — see .env.example.
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- app ---
    APP_NAME: str = "LLM-ERP"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_JSON: bool = False

    # --- database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./erp.db"
    DATABASE_URL_PROD: str = "postgresql+asyncpg://user:pass@localhost:5432/erp"
    DATABASE_DRIVER: Literal["sqlite", "postgresql"] = "sqlite"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # --- auth ---
    JWT_SECRET: str = "change-me-in-production-please-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    # If true and JWT_SECRET is the default, allow Bearer "demo" to login as super-admin.
    # Production deploys MUST set a real JWT_SECRET; demo-bypass auto-disables in that case.
    ALLOW_DEMO_BYPASS: bool = True

    # --- LLM ---
    LLM_PROVIDER: Literal["anthropic", "openai", "deepseek", "ollama"] = "deepseek"
    LLM_MODEL: str = "deepseek-chat"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MAX_TOOL_ROUNDS: int = 5
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_VERIFY_SSL: bool = True  # Windows dev 環境若 CA store 失效可設 False

    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- MESH / Factory ---
    FACTORY_MODE: Literal["hq", "factory"] = "hq"
    FACTORY_ID: str = "hq"
    FACTORY_NODES: list[str] = [
        "http://factory-a:8001",
        "http://factory-b:8002",
        "http://factory-c:8003",
    ]
    MESH_TIMEOUT_SECONDS: int = 5

    # --- middleware ---
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173", "http://localhost:19006",
        "http://localhost:8080", "http://localhost:3000",
    ]
    EVENT_SSE_ENABLED: bool = True
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_SKIP_PATHS: list[str] = [
        "/api/health", "/api/events/stream", "/docs",
        "/openapi.json", "/redoc", "/favicon.ico",
    ]

    # --- seed ---
    SEED_ADMIN_USERNAME: str = "admin"
    SEED_ADMIN_PASSWORD: str = "admin123"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def effective_db_url(self) -> str:
        return self.DATABASE_URL_PROD if self.DATABASE_DRIVER == "postgresql" else self.DATABASE_URL

    @property
    def demo_bypass_active(self) -> bool:
        """Demo bypass only works while JWT_SECRET is the default — production safety."""
        return self.ALLOW_DEMO_BYPASS and "change-me" in self.JWT_SECRET


settings = Settings()
