"""Centralised settings (pydantic-settings, env-driven).

Override via .env file or environment variables — see .env.example.
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- app ---
    APP_NAME: str = "Ouvoca"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_JSON: bool = False

    # --- database ---
    # sqlite 預設路徑：環境變數沒設時用相對路徑 ./erp.db。
    # ⚠️ docker 環境一定要由 docker-compose 環境變數覆蓋為絕對路徑
    #    （sqlite+aiosqlite:////app/data/erp.db）以對應 volume mount；
    #    否則 backend 從不同 CWD 啟動會產生新空 DB，看起來「資料不見了」。
    # 若要從專案根目錄跑 backend，建議在 backend/.env 設定：
    #    DATABASE_URL=sqlite+aiosqlite:///./backend/data/erp.db
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
    # 預設關閉；正式測試需明確設 true（避免任何環境意外開啟 Bearer demo 後門）
    ALLOW_DEMO_BYPASS: bool = False

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
    # CORS：同時列 localhost 和 127.0.0.1 兩種寫法 —
    # Windows 上 localhost 可能解析到 IPv6 ::1，瀏覽器自動 fallback 用 127.0.0.1，
    # 若只列 localhost 會被 CORS 擋導致「所有表單 POST 失敗」（v3.25.7 教訓 #38）。
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:8080", "http://127.0.0.1:8080",
        "http://localhost:19006", "http://127.0.0.1:19006",
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

    # --- v3.42 R4：per-user AI 用量限制（每人每日 LLM call 上限） ---
    AI_DAILY_LIMIT_PER_USER: int = 200

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
