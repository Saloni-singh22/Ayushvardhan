"""
Core configuration module for NAMASTE & ICD-11 TM2 Integration API
Handles environment variables and application settings with 2025 compliance standards
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with FHIR R4 and ABHA integration support"""
    
    # Application Configuration
    app_name: str = Field(default="NAMASTE-ICD11-TM2-API")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    reload: bool = Field(default=False)
    
    # Database Configuration - MongoDB
    mongodb_url: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="namaste_icd11_db")
    mongodb_min_connections: int = Field(default=10)
    mongodb_max_connections: int = Field(default=100)
    
    # WHO ICD-11 API Configuration (2025)
    who_icd_api_base_url: str = Field(default="https://id.who.int/icd")
    who_icd_auth_url: str = Field(default="https://icdaccessmanagement.who.int/connect/token")
    who_icd_api_version: str = Field(default="release/11/2023-01/mms")
    who_client_id: str = Field(default="8237d65d-ff79-4de1-98a7-a0af96a555a9_939cdbf7-938d-474f-9825-eafec1575f75")
    who_client_secret: str = Field(default="J1heyJHJGRyEb5CJ6ykeS/HvdscMK/00rOwZwTd45YY=")
    who_icd_scope: str = Field(default="icdapi_access")
    
    # ABHA (Ayushman Bharat Digital Mission) Configuration
    abha_base_url: str = Field(default="https://dev.abdm.gov.in")
    abha_client_id: str = Field(default="demo_abha_client")
    abha_client_secret: str = Field(default="demo_abha_secret")
    abha_scope: str = Field(default="abha-enrol")
    abha_redirect_uri: str = Field(default="http://localhost:8000/auth/callback")
    
    # NAMASTE Portal Configuration
    namaste_portal_url: str = Field(default="https://namaste.ayush.gov.in")
    namaste_api_key: Optional[str] = Field(default=None)
    
    # JWT Configuration for ABHA OAuth 2.0
    jwt_secret_key: str = Field(default="dev_jwt_secret_key_12345")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)
    jwt_refresh_token_expire_days: int = Field(default=7)
    
    # FHIR R4 Configuration
    fhir_base_url: str = Field(default="http://localhost:8000/api/v1")
    fhir_version: str = Field(default="4.0.1")
    terminology_service_url: str = Field(default="http://localhost:8000/api/v1")
    
    # Encryption Configuration for ABHA
    rsa_public_key_path: str = Field(default="config/keys/abha_public.pem")
    rsa_private_key_path: str = Field(default="config/keys/abha_private.pem")
    
    # Cache Configuration
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_ttl_seconds: int = Field(default=3600)
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=100)
    rate_limit_burst: int = Field(default=20)
    
    # Audit & Compliance (India EHR Standards 2016)
    audit_log_enabled: bool = Field(default=True)
    audit_log_level: str = Field(default="INFO")
    consent_tracking_enabled: bool = Field(default=True)
    version_tracking_enabled: bool = Field(default=True)
    
    # AI/ML Configuration for Code Mapping
    ml_model_path: str = Field(default="models/")
    similarity_threshold: float = Field(default=0.85)
    mapping_confidence_threshold: float = Field(default=0.90)
    
    # External Service Timeouts
    http_timeout_seconds: int = Field(default=30)
    who_api_timeout_seconds: int = Field(default=45)
    abha_api_timeout_seconds: int = Field(default=30)
    
    # CORS and Security
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000", 
            "http://localhost:8080",
            "http://localhost:4173",  # Vite preview
            "http://localhost:5173",  # Vite dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:4173",
            "http://127.0.0.1:5173"   # Vite dev server
        ]
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1", "*"]
    )
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret key is secure"""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("allowed_hosts", mode="before")
    @classmethod
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