import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "Pulsecast API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./pulsecast.db"
    DB_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pulsecast.db")

    # NDMA
    NDMA_BASE_URL: str = "https://knowledgeweb.ndma.go.ke"
    NDMA_BULLETIN_PATH: str = "/api/drought-bulletins"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

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
