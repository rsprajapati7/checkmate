from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://checkmate:password@localhost:5432/checkmate"
    REDIS_URL: str = "redis://localhost:6379/0"
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "gemma2"
    YOLO_MODEL_PATH: str = "models/yolov8/seal_detector.pt"

    class Config:
        env_file = ".env"

settings = Settings()
