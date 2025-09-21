"""
FHIR R4 ConceptMap API routes
Implements FHIR terminology service endpoints for ConceptMap resources
Includes NAMASTE to ICD-11 dual-coding mappings
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, Path
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from app.core.config import get_settings
from app.database.connection import get_database
from app.models.fhir.resources import ConceptMap, Bundle, BundleEntry
from app.models.namaste.traditional_medicine import NAMASTEConceptMap, DualCodingConcept
from app.models.who.icd11 import ICD11ConceptMap, ICD11ToNAMASTEMapping
from app.models.database import ConceptMapDBModel
from app.middlewares.auth_middleware import get_current_user
from app.utils.fhir_utils import create_operation_outcome, create_bundle_response
from app.utils.pagination import PaginationParams, paginate_results

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ConceptMap"])
settings = get_settings()


@router.get("", response_model=Bundle, summary="Search ConceptMaps")
async def search_concept_maps(
    url: Optional[str] = Query(None, description="Canonical URL of the ConceptMap"),
    name: Optional[str] = Query(None, description="Computer-friendly name"),
    title: Optional[str] = Query(None, description="Human-friendly title"),
    status: Optional[str] = Query(None, description="Publication status", pattern="^(draft|active|retired|unknown)$"),
    source: Optional[str] = Query(None, description="Source ValueSet or CodeSystem"),
    target: Optional[str] = Query(None, description="Target ValueSet or CodeSystem"),
    source_code: Optional[str] = Query(None, description="Source concept code", alias="source-code"),
    target_code: Optional[str] = Query(None, description="Target concept code", alias="target-code"),
    traditional_system: Optional[str] = Query(None, description="Traditional medicine system for NAMASTE maps"),
    biomedical_target: Optional[str] = Query(None, description="Biomedical target system"),
    _text: Optional[str] = Query(None, description="Full-text search", alias="_text"),
    _count: int = Query(50, ge=1, le=1000, description="Number of results per page"),
    _offset: int = Query(0, ge=0, description="Starting offset"),
    _sort: Optional[str] = Query("name", description="Sort field"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Search for ConceptMap resources with FHIR R4 compliance
    Supports NAMASTE to ICD-11 mappings and traditional medicine dual-coding
    """
    try:
        db_model = ConceptMapDBModel(db.conceptmaps)
        
        # Build MongoDB query
        query = {}
        
        if url:
            query["url"] = url
        if name:
            query["name"] = {"$regex": name, "$options": "i"}
        if title:
            query["title"] = {"$regex": title, "$options": "i"}
        if status:
            query["status"] = status
        if source:
            query["source"] = source
        if target:
            query["target"] = target
        if traditional_system:
            query["traditional_system"] = traditional_system
        if biomedical_target:
            query["biomedical_target"] = biomedical_target
        
        # Code-level searches
        if source_code:
            query["group.element.code"] = source_code
        if target_code:
            query["group.element.target.code"] = target_code
        
        # Full-text search
        if _text:
            query["$text"] = {"$search": _text}
        
        # Execute search with pagination
        cursor = db.conceptmaps.find(query)
        
        # Apply sorting
        if _sort:
            sort_direction = 1
            if _sort.startswith("-"):
                sort_direction = -1
                _sort = _sort[1:]
            cursor = cursor.sort(_sort, sort_direction)
        
        # Get total count
        total = await db.conceptmaps.count_documents(query)
        
        # Apply pagination
        cursor = cursor.skip(_offset).limit(_count)
        results = await cursor.to_list(length=None)
        
        # Convert to FHIR Bundle
        entries = []
        for doc in results:
            # Convert MongoDB document to FHIR ConceptMap
            concept_map = db_model.from_dict(doc, ConceptMap)
            if concept_map:
                entry = BundleEntry(
                    fullUrl=f"{settings.fhir_base_url}/ConceptMap/{concept_map.id}",
                    resource=concept_map
                )
                entries.append(entry)
        
        # Create search Bundle
        bundle = Bundle(
            type="searchset",
            timestamp=datetime.utcnow(),
            total=total,
            entry=entries
        )
        
        return bundle
        
    except Exception as e:
        logger.error(f"Error searching ConceptMaps: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=ConceptMap, summary="Read ConceptMap")
async def read_concept_map(
    id: str = Path(..., description="ConceptMap logical ID"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Read a specific ConceptMap resource by ID
    Returns FHIR R4 compliant ConceptMap
    """
    try:
        db_model = ConceptMapDBModel(db.conceptmaps)
        
        # Find by MongoDB _id or by id field
        doc = await db.conceptmaps.find_one({"$or": [{"_id": id}, {"id": id}]})
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"ConceptMap with id '{id}' not found"
                )
            )
        
        # Convert to FHIR ConceptMap
        concept_map = db_model.from_dict(doc, ConceptMap)
        if not concept_map:
            raise HTTPException(status_code=500, detail="Error converting ConceptMap")
        
        return concept_map
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading ConceptMap {id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=ConceptMap, summary="Create ConceptMap")
async def create_concept_map(
    concept_map: ConceptMap,
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Create a new ConceptMap resource
    Validates FHIR R4 compliance and stores in MongoDB
    """
    try:
        db_model = ConceptMapDBModel(db.conceptmaps)
        
        # Validate canonical URL uniqueness
        if concept_map.url:
            existing = await db.conceptmaps.find_one({
                "url": concept_map.url,
                "version": concept_map.version
            })
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=create_operation_outcome(
                        "error",
                        "duplicate",
                        f"ConceptMap with URL '{concept_map.url}' and version '{concept_map.version}' already exists"
                    )
                )
        
        # Set metadata
        if not concept_map.id:
            from bson import ObjectId
            concept_map.id = str(ObjectId())
        
        if not concept_map.meta:
            from app.models.fhir.base import Meta
            concept_map.meta = Meta(
                versionId="1",
                lastUpdated=datetime.utcnow()
            )
        
        # Convert to MongoDB document
        doc = db_model.to_dict(concept_map)
        
        # Insert into database
        result = await db.conceptmaps.insert_one(doc)
        
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create ConceptMap")
        
        # Return created resource
        created_doc = await db.conceptmaps.find_one({"_id": result.inserted_id})
        created_concept_map = db_model.from_dict(created_doc, ConceptMap)
        
        return created_concept_map
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ConceptMap: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}/$translate", summary="Translate Concept")
async def translate_concept(
    id: str = Path(..., description="ConceptMap logical ID"),
    code: Optional[str] = Query(None, description="Source code to translate"),
    system: Optional[str] = Query(None, description="Source code system"),
    target: Optional[str] = Query(None, description="Target system or ValueSet"),
    reverse: bool = Query(False, description="Reverse translation"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Translate a concept using the ConceptMap
    Returns FHIR Parameters resource with translation results
    """
    try:
        db_model = ConceptMapDBModel(db.conceptmaps)
        
        # Find ConceptMap
        doc = await db.conceptmaps.find_one({"$or": [{"_id": id}, {"id": id}]})
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"ConceptMap with id '{id}' not found"
                )
            )
        
        # Find matching translations
        matches = []
        
        if doc.get("group"):
            for group in doc["group"]:
                # Check if source system matches
                if system and group.get("source") != system:
                    continue
                
                # Check if target system matches
                if target and group.get("target") != target:
                    continue
                
                # Search for code in elements
                if group.get("element"):
                    for element in group["element"]:
                        element_code = element.get("code")
                        
                        if not reverse and element_code == code:
                            # Forward translation
                            if element.get("target"):
                                for target_elem in element["target"]:
                                    match = {
                                        "equivalence": target_elem.get("equivalence", "equivalent"),
                                        "concept": {
                                            "system": group.get("target"),
                                            "code": target_elem.get("code"),
                                            "display": target_elem.get("display")
                                        }
                                    }
                                    if target_elem.get("comment"):
                                        match["comment"] = target_elem["comment"]
                                    matches.append(match)
                        
                        elif reverse and element.get("target"):
                            # Reverse translation
                            for target_elem in element["target"]:
                                if target_elem.get("code") == code:
                                    match = {
                                        "equivalence": target_elem.get("equivalence", "equivalent"),
                                        "concept": {
                                            "system": group.get("source"),
                                            "code": element_code,
                                            "display": element.get("display")
                                        }
                                    }
                                    if target_elem.get("comment"):
                                        match["comment"] = target_elem["comment"]
                                    matches.append(match)
        
        # Create Parameters response
        parameters = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "result",
                    "valueBoolean": len(matches) > 0
                }
            ]
        }
        
        if matches:
            for match in matches:
                match_param = {
                    "name": "match",
                    "part": [
                        {
                            "name": "equivalence",
                            "valueCode": match["equivalence"]
                        },
                        {
                            "name": "concept",
                            "valueCoding": match["concept"]
                        }
                    ]
                }
                
                if match.get("comment"):
                    match_param["part"].append({
                        "name": "comment",
                        "valueString": match["comment"]
                    })
                
                parameters["parameter"].append(match_param)
        else:
            parameters["parameter"].append({
                "name": "message",
                "valueString": f"No translation found for code '{code}' in system '{system}'"
            })
        
        return JSONResponse(content=parameters)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error translating concept: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# NAMASTE-specific ConceptMap endpoints
@router.get("/namaste/search", response_model=Bundle, summary="Search NAMASTE ConceptMaps")
async def search_namaste_concept_maps(
    traditional_system: Optional[str] = Query(None, description="Traditional medicine system"),
    biomedical_target: Optional[str] = Query(None, description="Biomedical target system"),
    source_ayush_system: Optional[str] = Query(None, description="Source AYUSH system"),
    confidence_threshold: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    _count: int = Query(50, ge=1, le=1000),
    _offset: int = Query(0, ge=0),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Search NAMASTE traditional medicine to biomedical ConceptMaps
    Includes Ayurveda, Siddha, Unani to ICD-11 mappings
    """
    try:
        query = {"traditional_system": {"$exists": True}}
        
        if traditional_system:
            query["traditional_system"] = traditional_system
        
        if biomedical_target:
            query["biomedical_target"] = biomedical_target
        
        if source_ayush_system:
            query["dual_concepts.traditional_concept.system"] = source_ayush_system
        
        if confidence_threshold:
            query["dual_concepts.mapping_confidence"] = {"$gte": confidence_threshold}
        
        cursor = db.conceptmaps.find(query).skip(_offset).limit(_count)
        results = await cursor.to_list(length=None)
        total = await db.conceptmaps.count_documents(query)
        
        # Convert to Bundle
        entries = []
        db_model = ConceptMapDBModel(db.conceptmaps)
        
        for doc in results:
            concept_map = db_model.from_dict(doc, NAMASTEConceptMap)
            if concept_map:
                entry = BundleEntry(
                    fullUrl=f"{settings.fhir_base_url}/ConceptMap/{concept_map.id}",
                    resource=concept_map
                )
                entries.append(entry)
        
        bundle = Bundle(
            type="searchset",
            timestamp=datetime.utcnow(),
            total=total,
            entry=entries
        )
        
        return bundle
        
    except Exception as e:
        logger.error(f"Error searching NAMASTE ConceptMaps: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/namaste/{id}/dual-coding", summary="Get Dual-Coding Mappings")
async def get_dual_coding_mappings(
    id: str = Path(..., description="NAMASTE ConceptMap ID"),
    traditional_code: Optional[str] = Query(None, description="Traditional medicine code"),
    biomedical_code: Optional[str] = Query(None, description="Biomedical code"),
    confidence_threshold: Optional[float] = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Get dual-coding mappings from NAMASTE ConceptMap
    Returns traditional medicine concepts with biomedical equivalents
    """
    try:
        # Find ConceptMap
        doc = await db.conceptmaps.find_one({"$or": [{"_id": id}, {"id": id}]})
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"ConceptMap with id '{id}' not found"
                )
            )
        
        # Extract dual-coding concepts
        dual_concepts = doc.get("dual_concepts", [])
        
        # Filter by criteria
        filtered_concepts = []
        for concept in dual_concepts:
            # Check confidence threshold
            if concept.get("mapping_confidence", 0) < confidence_threshold:
                continue
            
            # Check traditional code filter
            if traditional_code:
                trad_concept = concept.get("traditional_concept", {})
                if trad_concept.get("code") != traditional_code:
                    continue
            
            # Check biomedical code filter
            if biomedical_code:
                found_biomedical = False
                for icd_concept in concept.get("icd11_concepts", []):
                    if icd_concept.get("code") == biomedical_code:
                        found_biomedical = True
                        break
                for snomed_concept in concept.get("snomed_concepts", []):
                    if snomed_concept.get("code") == biomedical_code:
                        found_biomedical = True
                        break
                
                if not found_biomedical:
                    continue
            
            filtered_concepts.append(concept)
        
        # Create response
        response = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "conceptMap",
                    "valueReference": {
                        "reference": f"ConceptMap/{id}"
                    }
                },
                {
                    "name": "totalMappings",
                    "valueInteger": len(filtered_concepts)
                }
            ]
        }
        
        # Add dual-coding concepts
        for concept in filtered_concepts:
            concept_param = {
                "name": "dualCoding",
                "part": [
                    {
                        "name": "traditionalConcept",
                        "valueString": str(concept.get("traditional_concept", {}))
                    },
                    {
                        "name": "mappingConfidence",
                        "valueDecimal": concept.get("mapping_confidence", 0.0)
                    },
                    {
                        "name": "mappingType",
                        "valueString": concept.get("mapping_type", "unknown")
                    }
                ]
            }
            
            # Add biomedical mappings
            if concept.get("icd11_concepts"):
                concept_param["part"].append({
                    "name": "icd11Mappings",
                    "valueString": str(concept["icd11_concepts"])
                })
            
            if concept.get("snomed_concepts"):
                concept_param["part"].append({
                    "name": "snomedMappings", 
                    "valueString": str(concept["snomed_concepts"])
                })
            
            response["parameter"].append(concept_param)
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dual-coding mappings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/namaste/validate-mapping", summary="Validate NAMASTE Mapping")
async def validate_namaste_mapping(
    mapping_data: Dict[str, Any],
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Validate a NAMASTE to biomedical mapping
    Checks traditional medicine principles and biomedical accuracy
    """
    try:
        validation_results = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "valid",
                    "valueBoolean": True
                },
                {
                    "name": "validationDate",
                    "valueDateTime": datetime.utcnow().isoformat()
                }
            ]
        }
        
        errors = []
        warnings = []
        
        # Validate traditional concept
        traditional_concept = mapping_data.get("traditional_concept")
        if traditional_concept:
            # Check dosha consistency for Ayurveda
            if traditional_concept.get("system") == "ayurveda":
                ayurveda_props = traditional_concept.get("ayurveda_properties", {})
                doshas = ayurveda_props.get("doshagnata", [])
                
                # Example validation rule: ensure dosha balance
                if len(doshas) > 2:
                    warnings.append("Multiple dosha affinities may indicate complex interaction")
        
        # Validate biomedical mappings
        icd11_concepts = mapping_data.get("icd11_concepts", [])
        if icd11_concepts:
            for concept in icd11_concepts:
                # Check ICD-11 code format
                code = concept.get("code", "")
                if not code.startswith(("1", "2", "X")):  # Basic ICD-11 format check
                    errors.append(f"Invalid ICD-11 code format: {code}")
        
        # Validate mapping confidence
        confidence = mapping_data.get("mapping_confidence", 0)
        if confidence < 0.5:
            warnings.append("Low mapping confidence may require expert review")
        
        # Add validation results
        if errors:
            validation_results["parameter"][0]["valueBoolean"] = False
            validation_results["parameter"].append({
                "name": "errors",
                "valueString": "; ".join(errors)
            })
        
        if warnings:
            validation_results["parameter"].append({
                "name": "warnings",
                "valueString": "; ".join(warnings)
            })
        
        return JSONResponse(content=validation_results)
        
    except Exception as e:
        logger.error(f"Error validating NAMASTE mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
