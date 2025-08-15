"""
Configuration module for RAG System
Manages environment variables, database settings, and model configurations
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    
    # Database Settings
    DATABASE_PATH: str = "data/metadata.db"
    FAISS_INDEX_PATH: str = "data/indexes/faiss_index.idx"
    BM25_INDEX_PATH: str = "data/indexes/bm25_index.pkl"
    
    # Model Settings
    EMBEDDING_MODEL: str = "AITeamVN/Vietnamese_Embedding"
    EMBEDDING_DEVICE: str = "cuda" if os.getenv("CUDA_AVAILABLE") == "true" else "cpu"
    EMBEDDING_DIMENSION: int = 384
    
    # Search Settings  
    DEFAULT_TOP_K: int = 5
    COMPENSATION_FACTOR: int = 3
    MAX_RETRIES: int = 2
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/rag_system.log"
    
    # Security Settings
    ALLOWED_ORIGINS: List[str] = ["*"]  # Configure for production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    @validator('DATABASE_PATH', 'FAISS_INDEX_PATH', 'BM25_INDEX_PATH', 'LOG_FILE')
    def create_parent_dirs(cls, v):
        """Create parent directories if they don't exist"""
        path = Path(v)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

# Configure logging
def setup_logging():
    """Setup application logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.FileHandler(settings.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    # Set third-party loggers to WARNING
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

logger = setup_logging()