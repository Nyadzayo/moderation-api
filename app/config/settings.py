"""Application settings and configuration management."""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    env: str = Field(default="development", alias="ENV")
    api_version: str = Field(default="1.0.0", alias="API_VERSION")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")

    # Model Configuration
    default_model: str = Field(default="unitary/toxic-bert", alias="DEFAULT_MODEL")
    model_cache_dir: str = Field(default="./models_cache", alias="MODEL_CACHE_DIR")
    lazy_load_model: bool = Field(default=True, alias="LAZY_LOAD_MODEL")

    # Image Model Configuration
    default_image_model: str = Field(
        default="Falconsai/nsfw_image_detection",
        alias="DEFAULT_IMAGE_MODEL"
    )
    image_max_size_mb: int = Field(default=10, alias="IMAGE_MAX_SIZE_MB")
    image_max_dimension: int = Field(default=4096, alias="IMAGE_MAX_DIMENSION")
    image_url_timeout: int = Field(default=10, alias="IMAGE_URL_TIMEOUT")

    # Redis Configuration
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, alias="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: int = Field(default=5, alias="REDIS_SOCKET_CONNECT_TIMEOUT")
    redis_retry_on_timeout: bool = Field(default=True, alias="REDIS_RETRY_ON_TIMEOUT")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    # Caching
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")

    # Default Thresholds
    threshold_harassment: float = Field(default=0.7, alias="THRESHOLD_HARASSMENT")
    threshold_hate: float = Field(default=0.7, alias="THRESHOLD_HATE")
    threshold_profanity: float = Field(default=0.6, alias="THRESHOLD_PROFANITY")
    threshold_sexual: float = Field(default=0.7, alias="THRESHOLD_SEXUAL")
    threshold_spam: float = Field(default=0.8, alias="THRESHOLD_SPAM")
    threshold_violence: float = Field(default=0.6, alias="THRESHOLD_VIOLENCE")

    # CORS
    cors_origins: str = Field(default='["http://localhost:3000"]', alias="CORS_ORIGINS")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.cors_origins)
        except json.JSONDecodeError:
            return ["http://localhost:3000"]

    @property
    def default_thresholds(self) -> dict:
        """Get default thresholds as a dictionary."""
        return {
            "harassment": self.threshold_harassment,
            "hate": self.threshold_hate,
            "profanity": self.threshold_profanity,
            "sexual": self.threshold_sexual,
            "spam": self.threshold_spam,
            "violence": self.threshold_violence,
        }

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()