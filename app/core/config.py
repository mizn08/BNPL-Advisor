"""
Configuration settings for Z.AI application
"""
from pydantic_settings import BaseSettings
from typing import List
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )
    
    # Application
    APP_NAME: str = "Z.AI - Economic Empowerment & Decision Intelligence"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./z_ai.db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    
    # Security
    SECRET_KEY: str = "sk-6089acc1c3d7e37702b8439e0ea97c909695bfba7fbcbc23"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:8000",
    ]
    
    # Z.AI GLM Configuration (powered by ILMU Anthropic API)
    ZAI_GLM_API_URL: str = "https://api.ilmu.ai"
    ZAI_GLM_API_KEY: str = ""
    ZAI_GLM_MODEL: str = "ilmu-glm-5.1"
    ZAI_GLM_TIMEOUT: int = 120
    
    # AWS Configuration
    AWS_REGION: str = "ap-southeast-2"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    
# Create settings instance
settings = Settings()
