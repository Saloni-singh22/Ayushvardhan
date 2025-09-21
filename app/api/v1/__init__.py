"""
API v1 router module
Main router for all FHIR R4 terminology service endpoints
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

# Import route modules
from app.api.v1.routes.codesystem import router as codesystem_router
from app.api.v1.routes.conceptmap import router as conceptmap_router
from app.api.v1.routes.valueset import router as valueset_router
from app.utils.fhir_utils import create_capability_statement

# Create main API router
api_router = APIRouter()

# Include all route modules with appropriate prefixes
api_router.include_router(
    codesystem_router,
    prefix="/CodeSystem",
    tags=["CodeSystem", "Terminology"]
)

api_router.include_router(
    conceptmap_router,
    prefix="/ConceptMap",
    tags=["ConceptMap", "Terminology"]
)

api_router.include_router(
    valueset_router,
    prefix="/ValueSet", 
    tags=["ValueSet", "Terminology"]
)

# FHIR metadata endpoint
@api_router.get("/metadata", tags=["FHIR Metadata"])
async def get_capability_statement():
    """
    Return the CapabilityStatement for this FHIR R4 terminology server.
    
    This endpoint describes the capabilities of the terminology service including:
    - Supported FHIR resources (CodeSystem, ConceptMap, ValueSet)
    - Supported operations ($validate-code, $lookup, $translate, $expand)
    - Authentication requirements and search parameters
    """
    capability_statement = create_capability_statement(
        base_url="http://localhost:8000/api/v1",
        implementation_description="FHIR R4 Terminology Service with NAMASTE Traditional Medicine and WHO ICD-11 Integration",
        implementation_version="1.0.0"
    )
    return JSONResponse(content=capability_statement.dict())

# API health check endpoint
@api_router.get("/health", tags=["Health"])
async def api_health():
    """API health check endpoint for FHIR terminology service"""
    return {
        "status": "healthy",
        "service": "FHIR R4 Terminology Service",
        "version": "1.0.0",
        "description": "NAMASTE Traditional Medicine + WHO ICD-11 Integration",
        "supported_resources": ["CodeSystem", "ConceptMap", "ValueSet"],
        "supported_operations": ["$validate-code", "$lookup", "$translate", "$expand"]
    }

# Root endpoint that provides service information
@api_router.get("/", tags=["Root"])
async def root():
    """Root endpoint - returns FHIR terminology service information"""
    return {
        "resourceType": "TerminologyService",
        "id": "namaste-icd11-terminology",
        "name": "NAMASTE-ICD11 FHIR R4 Terminology Service",
        "status": "active",
        "description": "A FHIR R4-compliant terminology microservice integrating India's NAMASTE traditional medicine codes with WHO's ICD-11 TM2 and Biomedicine modules",
        "metadata_endpoint": "/api/v1/metadata",
        "base_url": "http://localhost:8000/api/v1",
        "supported_resources": [
            "CodeSystem", 
            "ConceptMap", 
            "ValueSet"
        ],
        "terminology_systems": [
            "NAMASTE Traditional Medicine",
            "WHO ICD-11 TM2",
            "WHO ICD-11 Biomedicine"
        ]
    }