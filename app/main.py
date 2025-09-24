"""
Main FastAPI application for NAMASTE & ICD-11 TM2 Integration
FHIR R4 compliant terminology microservice with ABHA authentication
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from typing import Dict, Any
import uvicorn

from app.core.config import settings
from app.database import startup_database, shutdown_database
from app.api.v1 import api_router
from app.middlewares.auth_middleware import AuthMiddleware
from app.middlewares.audit_middleware import AuditMiddleware


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log") if not settings.debug else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    await startup_database()
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await shutdown_database()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    **FHIR R4-compliant terminology microservice** that seamlessly integrates 
    India's NAMASTE codes with WHO's ICD-11 TM2 and Biomedicine modules.
    
    ## Features
    
    * **Dual-Coding Support**: NAMASTE + ICD-11 TM2 + Biomedicine
    * **FHIR R4 Compliance**: CodeSystem, ConceptMap, ValueSet, Bundle resources
    * **ABHA Integration**: OAuth 2.0 authentication with 14-digit ABHA numbers
    * **Real-time Sync**: WHO ICD-11 2025 API integration
    * **AI-Powered Mapping**: Intelligent code translation
    * **India EHR Standards 2016**: Full compliance with audit trails
    
    ## API Documentation
    
    * **FHIR Endpoints**: `/fhir/*` - Standard FHIR R4 operations
    * **Terminology**: `/api/v1/terminology/*` - Custom terminology operations  
    * **Authentication**: `/api/v1/auth/*` - ABHA OAuth 2.0 endpoints
    
    ## Compliance & Standards
    
    * ✅ FHIR R4 Terminology Service
    * ✅ WHO ICD-11 TM2 Integration
    * ✅ India EHR Standards 2016
    * ✅ ABHA OAuth 2.0 Authentication
    * ✅ ISO 22600 Access Control
    """,
    docs_url="/docs",  # Always enable docs for development
    redoc_url="/redoc",  # Always enable redoc for development
    openapi_url="/openapi.json",  # Always enable openapi for development
    lifespan=lifespan
)

# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

# Add CORS middleware - Enhanced for TypeScript frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "*",
        "Authorization",
        "Content-Type", 
        "X-Requested-With",
        "Accept",
        "Origin",
        "X-ABHA-Token",          # For ABHA authentication
        "X-Session-Id",          # For audit trails
        "X-Consent-Id",          # For consent tracking
        "X-Client-Version",      # For frontend version tracking
    ],
    expose_headers=[
        "X-Total-Count", 
        "X-Page-Count",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset"
    ]
)

# Add custom middlewares
app.add_middleware(AuditMiddleware)
app.add_middleware(AuthMiddleware)

# Include API routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "NAMASTE & ICD-11 TM2 Integration API",
        "fhir_version": settings.fhir_version,
        "endpoints": {
            "fhir_metadata": f"{settings.fhir_base_url}/metadata",
            "api_docs": "/docs" if settings.debug else "Documentation disabled in production",
            "health": "/health",
            "metrics": "/metrics"
        },
        "compliance": {
            "fhir_r4": True,
            "who_icd11_tm2": True,
            "india_ehr_2016": True,
            "abha_oauth2": True
        }
    }


@app.get("/health", tags=["Health"])
async def health_check(request: Request) -> Dict[str, Any]:
    """Health check endpoint"""
    from app.database import mongodb
    
    db_healthy = await mongodb.health_check()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "timestamp": time.time(),
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
        "database": {
            "mongodb": "connected" if db_healthy else "disconnected"
        },
        "services": {
            "fhir_terminology": "active",
            "who_icd_api": "configured",
            "abha_auth": "configured",
            "namaste_integration": "active"
        }
    }


@app.get("/fhir/metadata", tags=["FHIR"])
async def fhir_capability_statement() -> Dict[str, Any]:
    """FHIR R4 CapabilityStatement - declares server capabilities"""
    return {
        "resourceType": "CapabilityStatement",
        "id": "namaste-icd11-terminology-server",
        "url": f"{settings.fhir_base_url}/metadata",
        "version": settings.app_version,
        "name": "NAMASTE_ICD11_TM2_TerminologyServer",
        "title": "NAMASTE & ICD-11 TM2 FHIR Terminology Server",
        "status": "active",
        "date": "2025-09-22",
        "publisher": "NAMASTE & ICD-11 TM2 Integration Project",
        "description": "FHIR R4 Terminology Server for NAMASTE and WHO ICD-11 TM2 integration",
        "kind": "instance",
        "software": {
            "name": settings.app_name,
            "version": settings.app_version,
            "releaseDate": "2025-09-22"
        },
        "implementation": {
            "description": "NAMASTE & ICD-11 TM2 FHIR Terminology Server",
            "url": settings.fhir_base_url
        },
        "fhirVersion": settings.fhir_version,
        "format": ["json", "xml"],
        "rest": [
            {
                "mode": "server",
                "documentation": "FHIR R4 Terminology Service supporting NAMASTE and WHO ICD-11 TM2",
                "security": {
                    "cors": True,
                    "service": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/restful-security-service",
                                    "code": "OAuth",
                                    "display": "OAuth2 using ABHA"
                                }
                            ]
                        }
                    ],
                    "description": "ABHA OAuth 2.0 authentication required for protected resources"
                },
                "resource": [
                    {
                        "type": "CodeSystem",
                        "supportedProfile": [
                            "http://hl7.org/fhir/StructureDefinition/CodeSystem"
                        ],
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "url", "type": "uri"},
                            {"name": "version", "type": "token"},
                            {"name": "name", "type": "string"},
                            {"name": "title", "type": "string"},
                            {"name": "status", "type": "token"}
                        ],
                        "operation": [
                            {
                                "name": "lookup",
                                "definition": f"{settings.fhir_base_url}/OperationDefinition/CodeSystem-lookup"
                            },
                            {
                                "name": "validate-code",
                                "definition": f"{settings.fhir_base_url}/OperationDefinition/CodeSystem-validate-code"
                            }
                        ]
                    },
                    {
                        "type": "ConceptMap",
                        "supportedProfile": [
                            "http://hl7.org/fhir/StructureDefinition/ConceptMap"
                        ],
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "url", "type": "uri"},
                            {"name": "version", "type": "token"},
                            {"name": "source", "type": "reference"},
                            {"name": "target", "type": "reference"}
                        ],
                        "operation": [
                            {
                                "name": "translate",
                                "definition": f"{settings.fhir_base_url}/OperationDefinition/ConceptMap-translate"
                            }
                        ]
                    },
                    {
                        "type": "ValueSet",
                        "supportedProfile": [
                            "http://hl7.org/fhir/StructureDefinition/ValueSet"
                        ],
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "url", "type": "uri"},
                            {"name": "version", "type": "token"},
                            {"name": "name", "type": "string"},
                            {"name": "title", "type": "string"}
                        ],
                        "operation": [
                            {
                                "name": "expand",
                                "definition": f"{settings.fhir_base_url}/OperationDefinition/ValueSet-expand"
                            },
                            {
                                "name": "validate-code",
                                "definition": f"{settings.fhir_base_url}/OperationDefinition/ValueSet-validate-code"
                            }
                        ]
                    },
                    {
                        "type": "Bundle",
                        "supportedProfile": [
                            "http://hl7.org/fhir/StructureDefinition/Bundle"
                        ],
                        "interaction": [
                            {"code": "create"},
                            {"code": "read"}
                        ]
                    }
                ]
            }
        ]
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred"
            }
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )