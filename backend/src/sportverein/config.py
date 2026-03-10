from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./sportverein.db"
    secret_key: str = "dev-secret-key-change-in-production"
    token_expire_hours: int = 24
    admin_email: str = "admin@sportverein.de"

    model_config = {"env_file": ".env"}


settings = Settings()
