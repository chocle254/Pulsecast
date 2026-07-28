import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "Pulsecast API"
    DEBUG: bool = False

    # Database — Railway volume mount path, falls back to local
    # On Railway: set RAILWAY_VOLUME_MOUNT_PATH=/data in your service settings
    DB_PATH: str = os.environ.get(
        "DB_PATH",
        os.path.join(
            os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", os.path.dirname(os.path.dirname(__file__))),
            "pulsecast.db"
        )
    )

    # NDMA
    NDMA_BASE_URL: str = "https://knowledgeweb.ndma.go.ke"
    NDMA_BULLETIN_PATH: str = "/api/drought-bulletins"

    # LLM — Groq or NVIDIA NIM as fallback
    GROQ_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    # `llama-3.1-70b-versatile` was retired by Groq. This is Groq's
    # documented replacement for the subsequently retiring Llama 3.3 model.
    LLM_MODEL: str = "openai/gpt-oss-120b"

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://*.vercel.app",
    ]

    # Forecasting
    FORECAST_WEEKS: int = 6
    CONFIDENCE_LEVEL: float = 0.9

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
