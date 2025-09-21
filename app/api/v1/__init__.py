"""
API v1 router module
Main router for all API endpoints
"""

from fastapi import APIRouter

# Import routers when they're created
# from app.api.v1.fhir import router as fhir_router
# from app.api.v1.auth import router as auth_router
# from app.api.v1.terminology import router as terminology_router

# Create main API router
api_router = APIRouter()

# Placeholder endpoints for now
@api_router.get("/health")
async def api_health():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "message": "NAMASTE & ICD-11 TM2 Integration API v1"
    }

@api_router.get("/info")
async def api_info():
    """API information endpoint"""
    return {
        "name": "NAMASTE & ICD-11 TM2 Integration API",
        "version": "1.0.0",
        "description": "FHIR R4-compliant terminology microservice",
        "endpoints": {
            "fhir": "/fhir/*",
            "terminology": "/api/v1/terminology/*", 
            "authentication": "/api/v1/auth/*"
        },
        "features": [
            "NAMASTE code integration",
            "WHO ICD-11 TM2 mapping",
            "ABHA OAuth 2.0 authentication",
            "FHIR R4 compliance",
            "Dual-coding support"
        ]
    }

# Include sub-routers (will be uncommented as they're implemented)
# api_router.include_router(fhir_router, prefix="/fhir", tags=["FHIR"])
# api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(terminology_router, prefix="/terminology", tags=["Terminology"])