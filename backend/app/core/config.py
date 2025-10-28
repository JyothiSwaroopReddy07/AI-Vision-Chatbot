"""Application configuration settings"""

from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # Application
    APP_NAME: str = "Vision ChatBot Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Redis
    REDIS_URL: str
    REDIS_PASSWORD: Optional[str] = None
    
    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIR: str = "/data/chromadb"
    
    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # openai, anthropic, local
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Local LLM (optional)
    LOCAL_LLM_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.2"
    LOCAL_LLM_DEVICE: str = "cpu"
    LOCAL_LLM_MAX_LENGTH: int = 4096
    
    # Embedding
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 64
    
    # RAG Configuration
    RETRIEVAL_K: int = 5
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 2000
    TOP_P: float = 0.9
    
    # PubMed
    PUBMED_API_KEY: Optional[str] = None
    PUBMED_EMAIL: str = "vision.research.ai@example.com"
    PUBMED_MAX_RESULTS: int = 10000
    PUBMED_BATCH_SIZE: int = 100
    
    # File Upload
    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_SIZE: int = 50000000  # 50MB
    ALLOWED_EXTENSIONS: str = "pdf,txt,doc,docx,png,jpg,jpeg"
    
    # Storage
    PUBMED_PDF_DIR: str = "/data/pubmed_pdfs"
    PROCESSED_DATA_DIR: str = "/data/processed"
    LOGS_DIR: str = "/data/logs"
    
    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 3600
    
    # Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # CORS
    CORS_ENABLED: bool = True
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # OCR
    TESSERACT_PATH: str = "/usr/bin/tesseract"
    TESSERACT_LANG: str = "eng"
    
    # Pathway Analysis
    PATHWAY_DATABASES: str = "KEGG,Reactome,GO_BP,GO_MF,GO_CC"
    PATHWAY_P_VALUE_THRESHOLD: float = 0.05
    PATHWAY_FDR_METHOD: str = "fdr_bh"
    
    # MSigDB
    MSIGDB_HUMAN_DB_PATH: str = "/data/msigdb/msigdb_v2025.1.Hs.db"
    MSIGDB_MOUSE_DB_PATH: str = "/data/msigdb/msigdb_v2025.1.Mm.db"
    MSIGDB_P_VALUE_THRESHOLD: float = 0.05
    MSIGDB_FDR_METHOD: str = "fdr_bh"
    MSIGDB_MIN_GENE_SET_SIZE: int = 5
    MSIGDB_MAX_GENE_SET_SIZE: int = 500
    
    # Email (Optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@visionchatbot.com"
    
    # Sentry (Optional)
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "production"
    
    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def parse_allowed_origins(cls, v: str) -> List[str]:
        """Parse comma-separated origins"""
        return [origin.strip() for origin in v.split(",")]
    
    @field_validator("ALLOWED_EXTENSIONS")
    @classmethod
    def parse_allowed_extensions(cls, v: str) -> List[str]:
        """Parse comma-separated extensions"""
        return [ext.strip() for ext in v.split(",")]
    
    @field_validator("PATHWAY_DATABASES")
    @classmethod
    def parse_pathway_databases(cls, v: str) -> List[str]:
        """Parse comma-separated databases"""
        return [db.strip() for db in v.split(",")]


# Global settings instance
settings = Settings()

