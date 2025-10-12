"""Configuration for Dashboard Service"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service info
    SERVICE_NAME: str = "Dashboard Service"
    SERVICE_HOST: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8000"))
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "openmetadata_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "openmetadata_password")
    DB_NAME: str = os.getenv("DB_NAME", "openmetadata_db")
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "dashboards_db")
    
    # Query Service
    QUERY_SERVICE_URL: str = os.getenv("QUERY_SERVICE_URL", "http://query-service:8000")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    class Config:
        case_sensitive = True


settings = Settings()

