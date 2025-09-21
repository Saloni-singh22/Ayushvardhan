"""
Core configuration module for NAMASTE & ICD-11 TM2 Integration API
Handles environment variables and application settings with 2025 compliance standards
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with FHIR R4 and ABHA integration support"""
    
    # Application Configuration
    app_name: str = Field(default="NAMASTE-ICD11-TM2-API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=False, env="RELOAD")
    
    # Database Configuration - MongoDB
    mongodb_url: str = Field(env="MONGODB_URL")
    mongodb_database: str = Field(default="namaste_icd11_db", env="MONGODB_DATABASE")
    mongodb_min_connections: int = Field(default=10, env="MONGODB_MIN_CONNECTIONS")
    mongodb_max_connections: int = Field(default=100, env="MONGODB_MAX_CONNECTIONS")
    
    # WHO ICD-11 API Configuration (2025)
    who_icd_api_base_url: str = Field(
        default="https://icd.who.int/icdapi", 
        env="WHO_ICD_API_BASE_URL"
    )
    who_icd_api_key: str = Field(env="WHO_ICD_API_KEY")
    who_icd_api_version: str = Field(default="v2", env="WHO_ICD_API_VERSION")
    who_client_id: str = Field(env="WHO_CLIENT_ID")
    who_client_secret: str = Field(env="WHO_CLIENT_SECRET")
    
    # ABHA (Ayushman Bharat Digital Mission) Configuration
    abha_base_url: str = Field(
        default="https://dev.abdm.gov.in", 
        env="ABHA_BASE_URL"
    )
    abha_client_id: str = Field(env="ABHA_CLIENT_ID")
    abha_client_secret: str = Field(env="ABHA_CLIENT_SECRET")
    abha_scope: str = Field(default="abha-enrol", env="ABHA_SCOPE")
    abha_redirect_uri: str = Field(env="ABHA_REDIRECT_URI")
    
    # NAMASTE Portal Configuration
    namaste_portal_url: str = Field(
        default="https://namaste.ayush.gov.in", 
        env="NAMASTE_PORTAL_URL"
    )
    namaste_api_key: Optional[str] = Field(default=None, env="NAMASTE_API_KEY")
    
    # JWT Configuration for ABHA OAuth 2.0
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, 
        env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, 
        env="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )
    
    # FHIR R4 Configuration
    fhir_base_url: str = Field(env="FHIR_BASE_URL")
    fhir_version: str = Field(default="4.0.1", env="FHIR_VERSION")
    terminology_service_url: str = Field(env="TERMINOLOGY_SERVICE_URL")
    
    # Encryption Configuration for ABHA
    rsa_public_key_path: str = Field(
        default="config/keys/abha_public.pem", 
        env="RSA_PUBLIC_KEY_PATH"
    )
    rsa_private_key_path: str = Field(
        default="config/keys/abha_private.pem", 
        env="RSA_PRIVATE_KEY_PATH"
    )
    
    # Cache Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")
    
    # Audit & Compliance (India EHR Standards 2016)
    audit_log_enabled: bool = Field(default=True, env="AUDIT_LOG_ENABLED")
    audit_log_level: str = Field(default="INFO", env="AUDIT_LOG_LEVEL")
    consent_tracking_enabled: bool = Field(
        default=True, 
        env="CONSENT_TRACKING_ENABLED"
    )
    version_tracking_enabled: bool = Field(
        default=True, 
        env="VERSION_TRACKING_ENABLED"
    )
    
    # AI/ML Configuration for Code Mapping
    ml_model_path: str = Field(default="models/", env="ML_MODEL_PATH")
    similarity_threshold: float = Field(default=0.85, env="SIMILARITY_THRESHOLD")
    mapping_confidence_threshold: float = Field(
        default=0.90, 
        env="MAPPING_CONFIDENCE_THRESHOLD"
    )
    
    # External Service Timeouts
    http_timeout_seconds: int = Field(default=30, env="HTTP_TIMEOUT_SECONDS")
    who_api_timeout_seconds: int = Field(default=45, env="WHO_API_TIMEOUT_SECONDS")
    abha_api_timeout_seconds: int = Field(default=30, env="ABHA_API_TIMEOUT_SECONDS")
    
    # CORS and Security
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], 
        env="CORS_ORIGINS"
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"], 
        env="ALLOWED_HOSTS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("jwt_secret_key")
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret key is secure"""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @property
    def database_url(self) -> str:
        """Get complete database URL with database name"""
        return f"{self.mongodb_url}/{self.mongodb_database}"
    
    @property
    def who_api_headers(self) -> dict:
        """Get WHO API headers for authentication"""
        return {
            "API-Version": self.who_icd_api_version,
            "Accept": "application/json",
            "Accept-Language": "en",
            "Authorization": f"Bearer {self.who_icd_api_key}"
        }
    
    @property
    def fhir_capability_statement_url(self) -> str:
        """Get FHIR CapabilityStatement URL"""
        return f"{self.fhir_base_url}/metadata"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return not self.debug


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


# Global settings instance
settings = get_settings()