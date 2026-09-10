from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load local runtime configuration without exposing secrets to templates."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MEMO_", extra="ignore")

    openai_api_key: SecretStr = SecretStr("")
    database_path: Path = Path("data/memo.db")
