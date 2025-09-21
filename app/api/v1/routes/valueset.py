"""
FHIR R4 ValueSet API routes
Implements FHIR terminology service endpoints for ValueSet resources
Includes expansion and validation operations
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, Path
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from app.core.config import get_settings
from app.database.connection import get_database
from app.models.fhir.resources import ValueSet, Bundle, BundleEntry
from app.models.namaste.traditional_medicine import NAMASTEValueSet
from app.models.database import ValueSetDBModel
from app.middlewares.auth_middleware import get_current_user
from app.utils.fhir_utils import create_operation_outcome, create_bundle_response
from app.utils.pagination import PaginationParams, paginate_results

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ValueSet", tags=["ValueSet"])
settings = get_settings()


@router.get("", response_model=Bundle, summary="Search ValueSets")
async def search_value_sets(
    url: Optional[str] = Query(None, description="Canonical URL of the ValueSet"),
    name: Optional[str] = Query(None, description="Computer-friendly name"),
    title: Optional[str] = Query(None, description="Human-friendly title"),
    status: Optional[str] = Query(None, description="Publication status", pattern="^(draft|active|retired|unknown)$"),
    publisher: Optional[str] = Query(None, description="Publisher name"),
    expansion: Optional[str] = Query(None, description="Value set expansion identifier"),
    code: Optional[str] = Query(None, description="Code contained in the value set"),
    system: Optional[str] = Query(None, description="System URI for code filter"),
    ayush_domain: Optional[str] = Query(None, description="AYUSH domain for NAMASTE ValueSets"),
    clinical_specialty: Optional[str] = Query(None, description="Clinical specialty"),
    _text: Optional[str] = Query(None, description="Full-text search", alias="_text"),
    _count: int = Query(50, ge=1, le=1000, description="Number of results per page"),
    _offset: int = Query(0, ge=0, description="Starting offset"),
    _sort: Optional[str] = Query("name", description="Sort field"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Search for ValueSet resources with FHIR R4 compliance
    Supports NAMASTE traditional medicine and biomedical ValueSets
    """
    try:
        db_model = ValueSetDBModel(db.value_sets)
        
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
        if publisher:
            query["publisher"] = {"$regex": publisher, "$options": "i"}
        if expansion:
            query["expansion.identifier"] = expansion
        if ayush_domain:
            query["ayush_domain"] = ayush_domain
        if clinical_specialty:
            query["clinical_specialty"] = {"$regex": clinical_specialty, "$options": "i"}
        
        # Code and system filters
        if code:
            if system:
                query["$or"] = [
                    {"compose.include.concept.code": code, "compose.include.system": system},
                    {"expansion.contains.code": code, "expansion.contains.system": system}
                ]
            else:
                query["$or"] = [
                    {"compose.include.concept.code": code},
                    {"expansion.contains.code": code}
                ]
        
        # Full-text search
        if _text:
            query["$text"] = {"$search": _text}
        
        # Execute search with pagination
        cursor = db.value_sets.find(query)
        
        # Apply sorting
        if _sort:
            sort_direction = 1
            if _sort.startswith("-"):
                sort_direction = -1
                _sort = _sort[1:]
            cursor = cursor.sort(_sort, sort_direction)
        
        # Get total count
        total = await db.value_sets.count_documents(query)
        
        # Apply pagination
        cursor = cursor.skip(_offset).limit(_count)
        results = await cursor.to_list(length=None)
        
        # Convert to FHIR Bundle
        entries = []
        for doc in results:
            # Convert MongoDB document to FHIR ValueSet
            value_set = db_model.from_dict(doc, ValueSet)
            if value_set:
                entry = BundleEntry(
                    fullUrl=f"{settings.fhir_base_url}/ValueSet/{value_set.id}",
                    resource=value_set
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
        logger.error(f"Error searching ValueSets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=ValueSet, summary="Read ValueSet")
async def read_value_set(
    id: str = Path(..., description="ValueSet logical ID"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Read a specific ValueSet resource by ID
    Returns FHIR R4 compliant ValueSet
    """
    try:
        db_model = ValueSetDBModel(db.value_sets)
        
        # Find by MongoDB _id or by id field
        doc = await db.value_sets.find_one({"$or": [{"_id": id}, {"id": id}]})
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"ValueSet with id '{id}' not found"
                )
            )
        
        # Convert to FHIR ValueSet
        value_set = db_model.from_dict(doc, ValueSet)
        if not value_set:
            raise HTTPException(status_code=500, detail="Error converting ValueSet")
        
        return value_set
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading ValueSet {id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}/$expand", summary="Expand ValueSet")
async def expand_value_set(
    id: str = Path(..., description="ValueSet logical ID"),
    url: Optional[str] = Query(None, description="Canonical URL of ValueSet to expand"),
    filter: Optional[str] = Query(None, description="Text filter for expansion"),
    count: Optional[int] = Query(None, ge=1, le=1000, description="Number of codes to return"),
    offset: Optional[int] = Query(0, ge=0, description="Starting offset"),
    includeDesignations: bool = Query(False, description="Include concept designations"),
    designation: Optional[List[str]] = Query(None, description="Designations to include"),
    includeDefinition: bool = Query(False, description="Include concept definitions"),
    activeOnly: bool = Query(True, description="Include active concepts only"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Expand a ValueSet to return the list of codes
    Returns FHIR ValueSet with expansion containing matching concepts
    """
    try:
        db_model = ValueSetDBModel(db.value_sets)
        
        # Find ValueSet
        if url:
            doc = await db.value_sets.find_one({"url": url})
        else:
            doc = await db.value_sets.find_one({"$or": [{"_id": id}, {"id": id}]})
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"ValueSet not found"
                )
            )
        
        # Get compose definition
        compose = doc.get("compose", {})
        expansion_concepts = []
        
        # Process include elements
        for include in compose.get("include", []):
            include_system = include.get("system")
            
            # Handle explicit concept lists
            if include.get("concept"):
                for concept in include["concept"]:
                    concept_data = {
                        "system": include_system,
                        "code": concept.get("code"),
                        "display": concept.get("display")
                    }
                    
                    # Apply filters
                    if filter and filter.lower() not in (concept.get("display", "").lower()):
                        continue
                    
                    if activeOnly and concept.get("inactive"):
                        continue
                    
                    expansion_concepts.append(concept_data)
            
            # Handle value set includes
            elif include.get("valueSet"):
                for vs_url in include["valueSet"]:
                    # Find referenced ValueSet and include its concepts
                    ref_vs = await db.value_sets.find_one({"url": vs_url})
                    if ref_vs and ref_vs.get("expansion", {}).get("contains"):
                        for concept in ref_vs["expansion"]["contains"]:
                            if filter and filter.lower() not in (concept.get("display", "").lower()):
                                continue
                            expansion_concepts.append(concept)
            
            # Handle filter-based includes
            elif include.get("filter"):
                # Query CodeSystem for concepts matching filters
                if include_system:
                    code_system = await db.code_systems.find_one({"url": include_system})
                    if code_system and code_system.get("concept"):
                        for concept in code_system["concept"]:
                            concept_data = {
                                "system": include_system,
                                "code": concept.get("code"),
                                "display": concept.get("display")
                            }
                            
                            # Apply ValueSet filters
                            passes_filters = True
                            for vs_filter in include["filter"]:
                                property_code = vs_filter.get("property")
                                op = vs_filter.get("op")
                                value = vs_filter.get("value")
                                
                                # Basic filter implementation
                                if property_code == "concept" and op == "is-a":
                                    # Check if concept is a descendant of value
                                    if not concept.get("code", "").startswith(value):
                                        passes_filters = False
                                        break
                            
                            if passes_filters:
                                if filter and filter.lower() not in (concept.get("display", "").lower()):
                                    continue
                                expansion_concepts.append(concept_data)
        
        # Apply pagination
        total_concepts = len(expansion_concepts)
        if count:
            expansion_concepts = expansion_concepts[offset:offset + count]
        
        # Create expansion
        expansion = {
            "identifier": f"urn:uuid:{datetime.utcnow().isoformat()}",
            "timestamp": datetime.utcnow(),
            "total": total_concepts,
            "offset": offset,
            "contains": expansion_concepts
        }
        
        # Add expansion parameters
        expansion["parameter"] = [
            {"name": "activeOnly", "valueBoolean": activeOnly},
            {"name": "includeDesignations", "valueBoolean": includeDesignations},
            {"name": "includeDefinition", "valueBoolean": includeDefinition}
        ]
        
        if filter:
            expansion["parameter"].append({"name": "filter", "valueString": filter})
        
        # Create response ValueSet with expansion
        response_vs = dict(doc)
        response_vs["expansion"] = expansion
        
        # Remove MongoDB-specific fields
        response_vs.pop("_id", None)
        response_vs.pop("created_at", None)
        response_vs.pop("updated_at", None)
        
        return JSONResponse(content=response_vs)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error expanding ValueSet: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}/$validate-code", summary="Validate Code in ValueSet")
async def validate_code_in_valueset(
    id: str = Path(..., description="ValueSet logical ID"),
    url: Optional[str] = Query(None, description="Canonical URL of ValueSet"),
    code: Optional[str] = Query(None, description="Code to validate"),
    system: Optional[str] = Query(None, description="Code system URL"),
    display: Optional[str] = Query(None, description="Display value to validate"),
    abstract: Optional[bool] = Query(None, description="Whether code is abstract"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Validate that a code is in a ValueSet
    Returns FHIR Parameters resource with validation result
    """
    try:
        db_model = ValueSetDBModel(db.value_sets)
        
        # Find ValueSet
        if url:
            doc = await db.value_sets.find_one({"url": url})
        else:
            doc = await db.value_sets.find_one({"$or": [{"_id": id}, {"id": id}]})
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"ValueSet not found"
                )
            )
        
        # Check if code is in ValueSet
        is_valid = False
        found_display = None
        found_system = None
        
        # Check expansion first
        if doc.get("expansion", {}).get("contains"):
            for concept in doc["expansion"]["contains"]:
                if concept.get("code") == code:
                    if not system or concept.get("system") == system:
                        is_valid = True
                        found_display = concept.get("display")
                        found_system = concept.get("system")
                        break
        
        # Check compose if not found in expansion
        if not is_valid and doc.get("compose", {}).get("include"):
            for include in doc["compose"]["include"]:
                include_system = include.get("system")
                
                # Check explicit concepts
                if include.get("concept"):
                    for concept in include["concept"]:
                        if concept.get("code") == code:
                            if not system or include_system == system:
                                is_valid = True
                                found_display = concept.get("display")
                                found_system = include_system
                                break
                
                # Check if code exists in referenced CodeSystem
                elif include_system and (not system or include_system == system):
                    code_system = await db.code_systems.find_one({"url": include_system})
                    if code_system and code_system.get("concept"):
                        for concept in code_system["concept"]:
                            if concept.get("code") == code:
                                is_valid = True
                                found_display = concept.get("display")
                                found_system = include_system
                                break
                
                if is_valid:
                    break
        
        # Validate display if provided
        display_valid = True
        if display and found_display:
            display_valid = (display.lower() == found_display.lower())
        
        # Create Parameters response
        parameters = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "result",
                    "valueBoolean": is_valid and display_valid
                },
                {
                    "name": "code",
                    "valueCode": code
                }
            ]
        }
        
        if found_system:
            parameters["parameter"].append({
                "name": "system",
                "valueUri": found_system
            })
        
        if found_display:
            parameters["parameter"].append({
                "name": "display",
                "valueString": found_display
            })
        
        if not is_valid:
            parameters["parameter"].append({
                "name": "message",
                "valueString": f"Code '{code}' not found in ValueSet"
            })
        elif not display_valid:
            parameters["parameter"].append({
                "name": "message",
                "valueString": f"Display '{display}' does not match expected '{found_display}'"
            })
        
        return JSONResponse(content=parameters)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating code in ValueSet: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# NAMASTE-specific ValueSet endpoints
@router.get("/namaste/search", response_model=Bundle, summary="Search NAMASTE ValueSets")
async def search_namaste_value_sets(
    ayush_domain: Optional[str] = Query(None, description="AYUSH domain filter"),
    clinical_specialty: Optional[str] = Query(None, description="Clinical specialty"),
    dosha_focus: Optional[str] = Query(None, description="Dosha focus for Ayurveda"),
    traditional_category: Optional[str] = Query(None, description="Traditional medicine category"),
    _count: int = Query(50, ge=1, le=1000),
    _offset: int = Query(0, ge=0),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Search NAMASTE traditional medicine ValueSets
    Includes Ayurveda, Siddha, Unani terminology collections
    """
    try:
        query = {"ayush_domain": {"$exists": True}}
        
        if ayush_domain:
            query["ayush_domain"] = ayush_domain
        
        if clinical_specialty:
            query["clinical_specialty"] = {"$regex": clinical_specialty, "$options": "i"}
        
        if dosha_focus:
            query["dosha_focus"] = dosha_focus
        
        if traditional_category:
            query["traditional_category"] = {"$regex": traditional_category, "$options": "i"}
        
        cursor = db.value_sets.find(query).skip(_offset).limit(_count)
        results = await cursor.to_list(length=None)
        total = await db.value_sets.count_documents(query)
        
        # Convert to Bundle
        entries = []
        db_model = ValueSetDBModel(db.value_sets)
        
        for doc in results:
            value_set = db_model.from_dict(doc, NAMASTEValueSet)
            if value_set:
                entry = BundleEntry(
                    fullUrl=f"{settings.fhir_base_url}/ValueSet/{value_set.id}",
                    resource=value_set
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
        logger.error(f"Error searching NAMASTE ValueSets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=ValueSet, summary="Create ValueSet")
async def create_value_set(
    value_set: ValueSet,
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Create a new ValueSet resource
    Validates FHIR R4 compliance and stores in MongoDB
    """
    try:
        db_model = ValueSetDBModel(db.value_sets)
        
        # Validate canonical URL uniqueness
        if value_set.url:
            existing = await db.value_sets.find_one({
                "url": value_set.url,
                "version": value_set.version
            })
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=create_operation_outcome(
                        "error",
                        "duplicate",
                        f"ValueSet with URL '{value_set.url}' and version '{value_set.version}' already exists"
                    )
                )
        
        # Set metadata
        if not value_set.id:
            from bson import ObjectId
            value_set.id = str(ObjectId())
        
        if not value_set.meta:
            from app.models.fhir.base import Meta
            value_set.meta = Meta(
                versionId="1",
                lastUpdated=datetime.utcnow()
            )
        
        # Convert to MongoDB document
        doc = db_model.to_dict(value_set)
        
        # Insert into database
        result = await db.value_sets.insert_one(doc)
        
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create ValueSet")
        
        # Return created resource
        created_doc = await db.value_sets.find_one({"_id": result.inserted_id})
        created_value_set = db_model.from_dict(created_doc, ValueSet)
        
        return created_value_set
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ValueSet: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")