from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "pyq_parser"
    upload_dir: str = "uploads"
    materials_dir: str = "materials"
    max_upload_size_mb: int = 20
    classifier_backend: str = "rule_based"
    relationship_detector_backend: str = "rule_based"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:4b"
    ollama_embedding_model: str = "embeddinggemma"
    ollama_request_timeout_seconds: float = 300.0
    agent_max_iterations: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
