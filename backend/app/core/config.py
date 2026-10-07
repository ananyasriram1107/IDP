from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "pyq_parser"
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20
    classifier_backend: str = "rule_based"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
