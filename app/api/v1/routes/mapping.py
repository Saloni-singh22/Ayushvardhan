"""
NAMASTE-WHO TM2 Mapping API Endpoints
Implements the optimal architecture for dual coding system
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from app.services.namaste_who_mapping import namaste_who_mapping_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mapping", tags=["NAMASTE-WHO TM2 Mapping"])


@router.post("/create-comprehensive",
            summary="Create Comprehensive NAMASTE ↔ WHO TM2 Mapping",
            description="Optimal approach: Map each NAMASTE term to WHO ICD-11 TM2 entities")
async def create_comprehensive_mapping(
    background_tasks: BackgroundTasks,
    force_refresh: bool = Query(False, description="Force refresh of existing mappings"),
    min_confidence: float = Query(0.3, ge=0.0, le=1.0, description="Minimum mapping confidence threshold")
):
    """
    Create comprehensive mapping between NAMASTE and WHO ICD-11 TM2
    
    This implements the optimal architecture:
    1. Extract all NAMASTE terms from existing CodeSystems
    2. Search WHO API for each NAMASTE term
    3. Create enhanced WHO TM2 CodeSystem with mapped entities
    4. Generate FHIR ConceptMap for NAMASTE ↔ WHO TM2
    5. Store results for translation operations
    
    Args:
        force_refresh: Whether to refresh existing mappings
        min_confidence: Minimum confidence score for mappings (0.0-1.0)
        
    Returns:
        dict: Mapping operation status and results
    """
    
    # Start background mapping process
    background_tasks.add_task(
        _run_comprehensive_mapping_background,
        force_refresh=force_refresh,
        min_confidence=min_confidence
    )
    
    return {
        "success": True,
        "message": "Comprehensive NAMASTE-WHO TM2 mapping started in background",
        "description": "This process will map each NAMASTE term to WHO ICD-11 TM2 entities",
        "parameters": {
            "force_refresh": force_refresh,
            "min_confidence": min_confidence
        },
        "timestamp": datetime.now().isoformat(),
        "note": "Check /mapping/status for progress updates"
    }


async def _run_comprehensive_mapping_background(force_refresh: bool, min_confidence: float):
    """Background task for comprehensive mapping"""
    
    try:
        logger.info("[MAPPING] Starting comprehensive NAMASTE-WHO TM2 mapping process")
        
        # Run the comprehensive mapping
        results = await namaste_who_mapping_service.create_comprehensive_mapping()
        
        logger.info(f"[SUCCESS] Comprehensive mapping completed: {results}")
        
    except Exception as e:
        logger.error(f"[ERROR] Comprehensive mapping failed: {e}")


@router.get("/status",
           summary="Get Mapping Status",
           description="Check the status of NAMASTE-WHO TM2 mapping operations")
async def get_mapping_status():
    """
    Get current status of NAMASTE-WHO TM2 mapping
    
    Returns:
        dict: Current mapping statistics and status
    """
    try:
        from app.database import get_database
        
        db = await get_database()
        
        # Get mapping metadata
        metadata = await db.mapping_metadata.find_one({"_id": "namaste_who_mapping_metadata"})
        
        if not metadata:
            return {
                "status": "not_started",
                "message": "No mapping operations have been performed yet",
                "timestamp": datetime.now().isoformat()
            }
        
        # Get CodeSystem and ConceptMap counts
        namaste_codesystems = await db.codesystems.count_documents({
            "source": {"$in": ["NAMASTE_AYURVEDA", "NAMASTE_SIDDHA", "NAMASTE_UNANI"]}
        })
        
        who_codesystems = await db.codesystems.count_documents({
            "source": "WHO_ICD11_TM2_NAMASTE_MAPPED"
        })
        
        concept_maps = await db.conceptmaps.count_documents({
            "id": "namaste-who-tm2-mapping"
        })
        
        return {
            "status": "completed" if metadata.get("successful_mappings", 0) > 0 else "failed",
            "mapping_statistics": {
                "total_namaste_terms": metadata.get("total_namaste_terms", 0),
                "successful_mappings": metadata.get("successful_mappings", 0),
                "success_rate": metadata.get("success_rate", 0),
                "last_updated": metadata.get("created_at")
            },
            "fhir_resources": {
                "namaste_codesystems": namaste_codesystems,
                "who_codesystems": who_codesystems,
                "concept_maps": concept_maps
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting mapping status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get mapping status: {str(e)}"
        )


@router.post("/translate",
            summary="Translate NAMASTE ↔ WHO TM2 Codes",
            description="Translation operation for dual coding")
async def translate_codes(
    source_system: str = Query(..., description="Source system: 'namaste' or 'who-tm2'"),
    source_code: str = Query(..., description="Source code to translate"),
    target_system: str = Query(..., description="Target system: 'namaste' or 'who-tm2'")
):
    """
    FHIR $translate operation for NAMASTE ↔ WHO TM2 codes
    
    Args:
        source_system: Source code system ('namaste' or 'who-tm2')
        source_code: Code to translate
        target_system: Target code system ('namaste' or 'who-tm2')
        
    Returns:
        dict: Translation results with mapped codes
    """
    try:
        from app.database import get_database
        
        db = await get_database()
        
        # Get the ConceptMap
        concept_map = await db.conceptmaps.find_one({"id": "namaste-who-tm2-mapping"})
        
        if not concept_map:
            raise HTTPException(
                status_code=404,
                detail="ConceptMap not found. Please run comprehensive mapping first."
            )
        
        # Search for translation
        translations = []
        
        for group in concept_map.get("group", []):
            for element in group.get("element", []):
                
                # Forward translation (NAMASTE → WHO TM2)
                if (source_system == "namaste" and target_system == "who-tm2" and 
                    element["code"] == source_code):
                    
                    for target in element.get("target", []):
                        translations.append({
                            "source_code": source_code,
                            "source_display": element["display"],
                            "target_code": target["code"],
                            "target_display": target["display"],
                            "equivalence": target.get("equivalence", "inexact"),
                            "confidence": target.get("comment", "")
                        })
                
                # Reverse translation (WHO TM2 → NAMASTE)
                elif (source_system == "who-tm2" and target_system == "namaste"):
                    for target in element.get("target", []):
                        if target["code"] == source_code:
                            translations.append({
                                "source_code": source_code,
                                "source_display": target["display"],
                                "target_code": element["code"],
                                "target_display": element["display"],
                                "equivalence": target.get("equivalence", "inexact"),
                                "confidence": target.get("comment", "")
                            })
        
        if not translations:
            return {
                "success": False,
                "message": f"No translation found for code '{source_code}' from '{source_system}' to '{target_system}'",
                "translations": [],
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "success": True,
            "source_system": source_system,
            "target_system": target_system,
            "translations": translations,
            "total_matches": len(translations),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Translation operation failed: {str(e)}"
        )


@router.get("/conceptmap",
           summary="Get NAMASTE-WHO TM2 ConceptMap",
           description="Retrieve the FHIR ConceptMap for NAMASTE ↔ WHO TM2 mapping")
async def get_conceptmap():
    """
    Get the FHIR ConceptMap for NAMASTE ↔ WHO TM2 mapping
    
    Returns:
        dict: FHIR ConceptMap resource
    """
    try:
        from app.database import get_database
        
        db = await get_database()
        
        concept_map = await db.conceptmaps.find_one({"id": "namaste-who-tm2-mapping"})
        
        if not concept_map:
            raise HTTPException(
                status_code=404,
                detail="ConceptMap not found. Please run comprehensive mapping first."
            )
        
        # Remove MongoDB _id field
        concept_map.pop("_id", None)
        
        return concept_map
        
    except Exception as e:
        logger.error(f"Error retrieving ConceptMap: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve ConceptMap: {str(e)}"
        )