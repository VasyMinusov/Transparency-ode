"""Конфигурация приложения. Все параметры — через переменные окружения с дефолтами."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    app_name: str = "transparency-api"
    database_url: str = "sqlite+aiosqlite:///./data/transparency.db"
    # GigaChat: оставляем пустым в MVP-скелете — объяснения генерируются заглушкой
    gigachat_credentials: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    # опциональный внешний прокси полных текстов НПА
    legal_api_url: str = ""
    # Фиксированный seed для воспроизводимости (требование паспорта: детерминированность)
    random_seed: int = 42
    # Восходящий агент: offline (детерминированный шаблон) | gigachat | ollama (локальная модель)
    llm_provider: str = "offline"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"


settings = Settings()
