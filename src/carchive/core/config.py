# carchive/src/carchive/core/config.py

try:
    # Try to import from pydantic-settings (Pydantic v2)
    from pydantic_settings import BaseSettings
    from pydantic import Field
    PYDANTIC_V2 = True
except ImportError:
    # Fall back to Pydantic v1
    from pydantic import BaseSettings, Field
    PYDANTIC_V2 = False

from typing import Optional
import keyring
import os

class Settings(BaseSettings):
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    ollama_url: str = Field(default="http://localhost:11434")
    # Default providers
    embedding_provider: str = Field(default="ollama")
    chat_provider: str = Field(default="ollama")
    content_provider: str = Field(default="ollama")
    multimodal_provider: str = Field(default="ollama")

    # Model configurations
    embedding_model_name: str = Field(default="nomic-embed-text")
    embedding_dimensions: int = Field(default=768)
    vision_model_name: str = Field(default="llama3.2-vision")
    text_model_name: str = Field(default="llama3.2")
    db_user: str = "carchive_app"
    db_password: Optional[str] = Field(default=None)
    db_host: str = "localhost"
    db_name: str = "carchive04_db"

    def build_database_url(self) -> str:
        password = keyring.get_password("carchive_app", "db_password") or self.db_password
        return f"postgresql://{self.db_user}:{password}@{self.db_host}/{self.db_name}"

    # Handle config for both Pydantic v1 and v2
    if PYDANTIC_V2:
        model_config = {
            "env_file": ".env",
            "env_file_encoding": "utf-8",
            "env_prefix": "",
            "extra": "ignore"
        }
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

    def get_secure_value(self, key: str, default=None):
        attr_name = key.lower()
        try:
            secure = keyring.get_password("carchive", key)
            return secure or getattr(self, attr_name, default)
        except Exception:
            return getattr(self, attr_name, default)

# Instantiate settings
settings = Settings()

# Backward compatibility assignments:
DATABASE_URL = settings.build_database_url()
OPENAI_API_KEY = settings.get_secure_value("OPENAI_API_KEY")
ANTHROPIC_API_KEY = settings.get_secure_value("ANTHROPIC_API_KEY")
OLLAMA_URL = settings.get_secure_value("OLLAMA_URL")
# Default providers
DEFAULT_EMBEDDING_PROVIDER = EMBEDDING_PROVIDER = settings.embedding_provider
DEFAULT_CHAT_PROVIDER = CHAT_PROVIDER = settings.chat_provider
DEFAULT_CONTENT_PROVIDER = CONTENT_PROVIDER = settings.content_provider
DEFAULT_MULTIMODAL_PROVIDER = MULTIMODAL_PROVIDER = settings.multimodal_provider

# Model settings
DEFAULT_EMBEDDING_MODEL = EMBEDDING_MODEL_NAME = settings.embedding_model_name
DEFAULT_EMBEDDING_DIMENSIONS = EMBEDDING_DIMENSIONS = settings.embedding_dimensions
VISION_MODEL_NAME = settings.vision_model_name
TEXT_MODEL_NAME = settings.text_model_name
