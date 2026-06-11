import sys
from pydantic_settings import BaseSettings
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

    # File upload
    UPLOAD_MAX_SIZE_MB: int = 50
    UPLOAD_TEMP_DIR: str = "./tmp/checkmate-uploads"
    OUTPUT_DIR: str = "./tmp/checkmate-output"

    # OCR
    TESSERACT_CMD: str = r"D:\Tessaract-OCR\tesseract.exe" if sys.platform == "win32" else "tesseract"

    # YOLOv8 seal detection
    YOLO_MODEL_PATH: str = "models/yolov8/seal_detector.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5

    # Risk thresholds
    RISK_GREEN_THRESHOLD: float = 0.30
    RISK_RED_THRESHOLD: float = 0.60

    # Fusion weights (must sum to 1.0)
    WEIGHT_ELA: float = 0.35
    WEIGHT_METADATA: float = 0.25
    WEIGHT_SEAL: float = 0.25
    WEIGHT_NLP: float = 0.15

    # API
    API_KEY_SECRET: str = "dev-secret-change-in-prod"
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


settings = Settings()

# Automatically adjust PostgreSQL URLs to use the async pg driver if necessary
if settings.DATABASE_URL.startswith("postgresql://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
