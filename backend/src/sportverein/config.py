from pathlib import Path

from pydantic_settings import BaseSettings

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "sportverein.db"


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{_DB_PATH}"
    secret_key: str = "dev-secret-key-change-in-production"
    token_expire_hours: int = 24
    admin_email: str = "admin@sportverein.de"

    model_config = {"env_file": ".env"}


settings = Settings()
