import sys
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Literal


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./checkmate.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM Settings
    LLM_PROVIDER: Literal["google", "ollama"] = "google"
    LLM_MODEL: str = "gemma-4-31b-it"
    GEMMA_API_KEY: str = ""
    OLLAMA_API_BASE: str = "http://localhost:11434"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT_SECONDS: float = 120.0

    # File upload
    UPLOAD_MAX_SIZE_MB: int = 50
    UPLOAD_TEMP_DIR: str = "./tmp/checkmate-uploads"
    OUTPUT_DIR: str = "./tmp/checkmate-output"

    # Frontend (for CORS restriction)
    FRONTEND_URL: str = "http://localhost:3000"

    # OCR
    TESSERACT_CMD: str = r"D:\Tessaract-OCR\tesseract.exe" if sys.platform == "win32" else "tesseract"

    # YOLOv8 seal detection
    YOLO_MODEL_PATH: str = "models/yolov8/seal_detector.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5

    # Risk thresholds
    RISK_GREEN_THRESHOLD: float = 0.30
    RISK_RED_THRESHOLD: float = 0.60

    # Fusion weights for SCANNED documents (must sum to 1.0)
    WEIGHT_ELA: float = 0.35
    WEIGHT_METADATA: float = 0.25
    WEIGHT_SEAL: float = 0.25
    WEIGHT_NLP: float = 0.15

    # Fusion weights for DIGITAL (native PDF) documents (must also sum to 1.0)
    WEIGHT_ELA_DIGITAL: float = 0.20
    WEIGHT_METADATA_DIGITAL: float = 0.45
    WEIGHT_SEAL_DIGITAL: float = 0.15
    WEIGHT_NLP_DIGITAL: float = 0.20

    # API
    API_KEY_SECRET: str = ""
    API_RATE_LIMIT: str = "100/minute"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        # Validate API key secret is set in production
        if self.ENVIRONMENT == "production" and self.API_KEY_SECRET in ("", "dev-secret-change-in-prod"):
            raise ValueError(
                "API_KEY_SECRET must be explicitly set in production. "
                "Set the API_KEY_SECRET environment variable."
            )

        # Validate scanned-document fusion weights sum to 1.0
        scanned_total = self.WEIGHT_ELA + self.WEIGHT_METADATA + self.WEIGHT_SEAL + self.WEIGHT_NLP
        if not (0.99 <= scanned_total <= 1.01):
            raise ValueError(
                f"Scanned-document fusion weights must sum to 1.0, got {scanned_total:.4f}. "
                f"Check WEIGHT_ELA, WEIGHT_METADATA, WEIGHT_SEAL, WEIGHT_NLP."
            )

        # Validate digital-document fusion weights sum to 1.0
        digital_total = (
            self.WEIGHT_ELA_DIGITAL + self.WEIGHT_METADATA_DIGITAL +
            self.WEIGHT_SEAL_DIGITAL + self.WEIGHT_NLP_DIGITAL
        )
        if not (0.99 <= digital_total <= 1.01):
            raise ValueError(
                f"Digital-document fusion weights must sum to 1.0, got {digital_total:.4f}. "
                f"Check WEIGHT_ELA_DIGITAL, WEIGHT_METADATA_DIGITAL, WEIGHT_SEAL_DIGITAL, WEIGHT_NLP_DIGITAL."
            )

        return self


settings = Settings()

# Automatically adjust PostgreSQL URLs to use the async pg driver if necessary
if settings.DATABASE_URL.startswith("postgresql://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
