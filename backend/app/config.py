import os
from typing import List, Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings for Solar Sentry Backend API."""

    PROJECT_NAME: str = Field(default="Solar Sentry Backend API")
    VERSION: str = Field(default="1.0.0")
    API_V1_STR: str = Field(default="/api/v1")
    ENVIRONMENT: str = Field(default=os.getenv("ENVIRONMENT", "development"))
    DEBUG: bool = Field(default=os.getenv("DEBUG", "True").lower() in ("true", "1", "t"))

    # Server binding
    HOST: str = Field(default=os.getenv("HOST", "0.0.0.0"))
    PORT: int = Field(default=int(os.getenv("PORT", "8000")))

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]

    # Storage paths
    IMAGE_STORAGE_PATH: str = Field(default=os.getenv("IMAGE_STORAGE_PATH", "data/images"))

    # Security / Auth prototype
    REQUIRE_API_KEY: bool = Field(default=os.getenv("REQUIRE_API_KEY", "False").lower() in ("true", "1", "t"))
    API_KEY: Optional[str] = Field(default=os.getenv("API_KEY", "solar-sentry-dev-key-2026"))
    EDGE_API_KEY: Optional[str] = Field(default=os.getenv("EDGE_API_KEY", "solar-sentry-edge-key-2026"))

    # Timeouts and intervals
    DEVICE_HEARTBEAT_TIMEOUT_SEC: int = Field(default=int(os.getenv("DEVICE_HEARTBEAT_TIMEOUT_SEC", "30")))
    DEFAULT_DEVICE_ID: str = Field(default=os.getenv("DEFAULT_DEVICE_ID", "esp32-sentry-01"))


settings = Settings()

