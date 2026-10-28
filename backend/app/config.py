from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PIPELINE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PIPELINE_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    database_url: str = f"sqlite:///{PIPELINE_ROOT / 'app.db'}"

    public_base_url: str = "http://localhost:8000"
    label_studio_url: str = "http://localhost:8080"
    label_studio_api_token: str = ""

    data_root: Path = PIPELINE_ROOT / "data"


settings = Settings()
settings.data_root.mkdir(parents=True, exist_ok=True)
