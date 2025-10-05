"""Configuration management for Query Service"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Service Configuration
    SERVICE_HOST: str = "query-service"
    SERVICE_PORT: int = 8000
    SERVICE_NAME: str = "Query Service"
    
    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379/1"
    
    # OpenMetadata Configuration
    OPENMETADATA_API_ENDPOINT: str = "http://openmetadata-server:8585/api"
    OPENMETADATA_JWT_TOKEN: str = ""
    OPENMETADATA_TIMEOUT: int = 30
    
    # Trino Configuration
    TRINO_HOST: str = "trino"
    TRINO_PORT: int = 8080
    TRINO_CATALOG: str = "iceberg"
    TRINO_SCHEMA: str = "default"
    TRINO_USER: str = "trino"
    TRINO_AUTH_TYPE: str = "none"
    TRINO_TIMEOUT: int = 300  # 5 minutes
    
    # Ollama Configuration
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_NL_MODEL: str = "llama3.1:70b"
    OLLAMA_CHART_MODEL: str = "llama3.1:8b"
    OLLAMA_TIMEOUT: int = 180  # 3 minutes - increased for chart generation
    OLLAMA_TEMPERATURE: float = 0.1
    
    # Workflow Configuration
    MAX_RETRIES: int = 2
    QUERY_TIMEOUT: int = 600  # 10 minutes (increased for multiple LLM calls)
    MAX_RESULT_ROWS: int = 10000
    
    # LangSmith Configuration (Optional)
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "democritus-query-service"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: Optional[str] = None
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

