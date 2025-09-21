"""
FHIR R4 CodeSystem API routes
Implements FHIR terminology service endpoints for CodeSystem resources
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, Path
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from app.core.config import get_settings
from app.database.connection import get_database
from app.models.fhir.resources import CodeSystem, Bundle, BundleEntry
from app.models.namaste.traditional_medicine import NAMASTECodeSystem, AyushSystemEnum
from app.models.who.icd11 import ICD11CodeSystem, ICD11ModuleEnum
from app.models.database import CodeSystemDBModel
from app.middlewares.auth_middleware import get_current_user
from app.utils.fhir_utils import create_operation_outcome, create_bundle_response
from app.utils.pagination import PaginationParams, paginate_results

logger = logging.getLogger(__name__)
router = APIRouter(tags=["CodeSystem"])
settings = get_settings()


@router.get("", response_model=Bundle, summary="Search CodeSystems")
async def search_code_systems(
    url: Optional[str] = Query(None, description="Canonical URL of the CodeSystem"),
    name: Optional[str] = Query(None, description="Computer-friendly name"),
    title: Optional[str] = Query(None, description="Human-friendly title"),
    status: Optional[str] = Query(None, description="Publication status", pattern="^(draft|active|retired|unknown)$"),
    publisher: Optional[str] = Query(None, description="Publisher name"),
    jurisdiction: Optional[str] = Query(None, description="Jurisdiction code"),
    content: Optional[str] = Query(None, description="Content type", pattern="^(not-present|example|fragment|complete|supplement)$"),
    ayush_system: Optional[AyushSystemEnum] = Query(None, description="AYUSH system filter for NAMASTE CodeSystems"),
    icd11_module: Optional[ICD11ModuleEnum] = Query(None, description="ICD-11 module filter"),
    _text: Optional[str] = Query(None, description="Full-text search", alias="_text"),
    _count: int = Query(50, ge=1, le=1000, description="Number of results per page"),
    _offset: int = Query(0, ge=0, description="Starting offset"),
    _sort: Optional[str] = Query("name", description="Sort field"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Search for CodeSystem resources with FHIR R4 compliance
    Supports NAMASTE traditional medicine and WHO ICD-11 CodeSystems
    """
    try:
        db_model = CodeSystemDBModel(db.code_systems)
        
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
        if content:
            query["content"] = content
        if ayush_system:
            query["ayush_system"] = ayush_system.value
        if icd11_module:
            query["icd11_module"] = icd11_module.value
        if jurisdiction:
            query["jurisdiction.coding.code"] = jurisdiction
        
        # Full-text search
        if _text:
            query["$text"] = {"$search": _text}
        
        # Execute search with pagination
        cursor = db.code_systems.find(query)
        
        # Apply sorting
        if _sort:
            sort_direction = 1
            if _sort.startswith("-"):
                sort_direction = -1
                _sort = _sort[1:]
            cursor = cursor.sort(_sort, sort_direction)
        
        # Get total count
        total = await db.code_systems.count_documents(query)
        
        # Apply pagination
        cursor = cursor.skip(_offset).limit(_count)
        results = await cursor.to_list(length=None)
        
        # Convert to FHIR Bundle
        entries = []
        for doc in results:
            # Convert MongoDB document to FHIR CodeSystem
            code_system = db_model.from_dict(doc, CodeSystem)
            if code_system:
                entry = BundleEntry(
                    fullUrl=f"{settings.fhir_base_url}/CodeSystem/{code_system.id}",
                    resource=code_system
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
        logger.error(f"Error searching CodeSystems: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=CodeSystem, summary="Read CodeSystem")
async def read_code_system(
    id: str = Path(..., description="CodeSystem logical ID"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Read a specific CodeSystem resource by ID
    Returns FHIR R4 compliant CodeSystem
    """
    try:
        db_model = CodeSystemDBModel(db.code_systems)
        
        # Find by MongoDB _id or by id field
        doc = await db.code_systems.find_one({"$or": [{"_id": id}, {"id": id}]})
        
        if not doc:
            raise HTTPException(
                status_code=404, 
                detail=create_operation_outcome(
                    "error", 
                    "not-found", 
                    f"CodeSystem with id '{id}' not found"
                )
            )
        
        # Convert to FHIR CodeSystem
        code_system = db_model.from_dict(doc, CodeSystem)
        if not code_system:
            raise HTTPException(status_code=500, detail="Error converting CodeSystem")
        
        return code_system
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading CodeSystem {id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=CodeSystem, summary="Create CodeSystem")
async def create_code_system(
    code_system: CodeSystem,
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Create a new CodeSystem resource
    Validates FHIR R4 compliance and stores in MongoDB
    """
    try:
        db_model = CodeSystemDBModel(db.code_systems)
        
        # Validate canonical URL uniqueness
        if code_system.url:
            existing = await db_model.find_by_url(code_system.url, code_system.version)
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=create_operation_outcome(
                        "error",
                        "duplicate",
                        f"CodeSystem with URL '{code_system.url}' and version '{code_system.version}' already exists"
                    )
                )
        
        # Set metadata
        if not code_system.id:
            from bson import ObjectId
            code_system.id = str(ObjectId())
        
        if not code_system.meta:
            from app.models.fhir.base import Meta
            code_system.meta = Meta(
                versionId="1",
                lastUpdated=datetime.utcnow()
            )
        
        # Convert to MongoDB document
        doc = db_model.to_dict(code_system)
        
        # Insert into database
        result = await db.code_systems.insert_one(doc)
        
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create CodeSystem")
        
        # Return created resource
        created_doc = await db.code_systems.find_one({"_id": result.inserted_id})
        created_code_system = db_model.from_dict(created_doc, CodeSystem)
        
        return created_code_system
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating CodeSystem: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{id}", response_model=CodeSystem, summary="Update CodeSystem")
async def update_code_system(
    id: str = Path(..., description="CodeSystem logical ID"),
    code_system: CodeSystem = None,
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Update an existing CodeSystem resource
    Performs full replacement with version increment
    """
    try:
        db_model = CodeSystemDBModel(db.code_systems)
        
        # Check if resource exists
        existing_doc = await db.code_systems.find_one({"$or": [{"_id": id}, {"id": id}]})
        if not existing_doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"CodeSystem with id '{id}' not found"
                )
            )
        
        # Set ID and update metadata
        code_system.id = id
        if code_system.meta:
            # Increment version
            current_version = int(code_system.meta.versionId or "0")
            code_system.meta.versionId = str(current_version + 1)
            code_system.meta.lastUpdated = datetime.utcnow()
        
        # Convert to MongoDB document
        doc = db_model.to_dict(code_system)
        doc["updated_at"] = datetime.utcnow()
        
        # Update in database
        result = await db.code_systems.replace_one(
            {"$or": [{"_id": id}, {"id": id}]},
            doc
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="CodeSystem not found")
        
        # Return updated resource
        updated_doc = await db.code_systems.find_one({"id": id})
        updated_code_system = db_model.from_dict(updated_doc, CodeSystem)
        
        return updated_code_system
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating CodeSystem {id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{id}", summary="Delete CodeSystem")
async def delete_code_system(
    id: str = Path(..., description="CodeSystem logical ID"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Delete a CodeSystem resource
    Marks as deleted or performs hard delete based on configuration
    """
    try:
        # Check if resource exists
        existing_doc = await db.code_systems.find_one({"$or": [{"_id": id}, {"id": id}]})
        if not existing_doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"CodeSystem with id '{id}' not found"
                )
            )
        
        # Perform deletion
        if settings.soft_delete:
            # Soft delete - mark as deleted
            await db.code_systems.update_one(
                {"$or": [{"_id": id}, {"id": id}]},
                {
                    "$set": {
                        "status": "retired",
                        "deleted_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        else:
            # Hard delete
            result = await db.code_systems.delete_one({"$or": [{"_id": id}, {"id": id}]})
            if result.deleted_count == 0:
                raise HTTPException(status_code=404, detail="CodeSystem not found")
        
        return JSONResponse(
            status_code=204,
            content=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting CodeSystem {id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}/$validate-code", summary="Validate Code")
async def validate_code(
    id: str = Path(..., description="CodeSystem logical ID"),
    code: Optional[str] = Query(None, description="Code to validate"),
    system: Optional[str] = Query(None, description="Code system URL"),
    display: Optional[str] = Query(None, description="Display value"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Validate a code against a CodeSystem
    Returns FHIR Parameters resource with validation result
    """
    try:
        db_model = CodeSystemDBModel(db.code_systems)
        
        # Find CodeSystem
        if system:
            doc = await db_model.find_by_url(system)
        else:
            doc = await db.code_systems.find_one({"$or": [{"_id": id}, {"id": id}]})
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"CodeSystem not found"
                )
            )
        
        # Validate code
        is_valid = False
        found_display = None
        
        if code and "concept" in doc:
            for concept in doc["concept"]:
                if concept.get("code") == code:
                    is_valid = True
                    found_display = concept.get("display")
                    break
        
        # Check display match if provided
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
        
        if found_display:
            parameters["parameter"].append({
                "name": "display",
                "valueString": found_display
            })
        
        if not is_valid:
            parameters["parameter"].append({
                "name": "message",
                "valueString": f"Code '{code}' not found in CodeSystem"
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
        logger.error(f"Error validating code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}/$lookup", summary="Concept Lookup")
async def lookup_concept(
    id: str = Path(..., description="CodeSystem logical ID"),
    code: str = Query(..., description="Code to lookup"),
    system: Optional[str] = Query(None, description="Code system URL"),
    property: Optional[List[str]] = Query(None, description="Properties to return"),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Lookup concept details in a CodeSystem
    Returns FHIR Parameters resource with concept information
    """
    try:
        db_model = CodeSystemDBModel(db.code_systems)
        
        # Find CodeSystem
        if system:
            doc = await db_model.find_by_url(system)
        else:
            doc = await db.code_systems.find_one({"$or": [{"_id": id}, {"id": id}]})
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    "CodeSystem not found"
                )
            )
        
        # Find concept
        concept_data = None
        if "concept" in doc:
            for concept in doc["concept"]:
                if concept.get("code") == code:
                    concept_data = concept
                    break
        
        if not concept_data:
            raise HTTPException(
                status_code=404,
                detail=create_operation_outcome(
                    "error",
                    "not-found",
                    f"Concept '{code}' not found in CodeSystem"
                )
            )
        
        # Build Parameters response
        parameters = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "name",
                    "valueString": doc.get("name", "")
                },
                {
                    "name": "version",
                    "valueString": doc.get("version", "")
                },
                {
                    "name": "display",
                    "valueString": concept_data.get("display", "")
                }
            ]
        }
        
        # Add definition if available
        if concept_data.get("definition"):
            parameters["parameter"].append({
                "name": "definition",
                "valueString": concept_data["definition"]
            })
        
        # Add properties if requested
        if property and concept_data.get("property"):
            for prop in concept_data["property"]:
                if not property or prop.get("code") in property:
                    param = {
                        "name": "property",
                        "part": [
                            {
                                "name": "code",
                                "valueCode": prop.get("code")
                            }
                        ]
                    }
                    
                    # Add property value based on type
                    if "valueString" in prop:
                        param["part"].append({
                            "name": "value",
                            "valueString": prop["valueString"]
                        })
                    elif "valueCode" in prop:
                        param["part"].append({
                            "name": "value",
                            "valueCode": prop["valueCode"]
                        })
                    
                    parameters["parameter"].append(param)
        
        return JSONResponse(content=parameters)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up concept: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# NAMASTE-specific CodeSystem endpoints
@router.get("/namaste/search", response_model=Bundle, summary="Search NAMASTE CodeSystems")
async def search_namaste_code_systems(
    ayush_system: Optional[AyushSystemEnum] = Query(None, description="AYUSH system filter"),
    traditional_name: Optional[str] = Query(None, description="Traditional name search"),
    dosha: Optional[str] = Query(None, description="Dosha filter"),
    _count: int = Query(50, ge=1, le=1000),
    _offset: int = Query(0, ge=0),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Search NAMASTE traditional medicine CodeSystems
    Includes Ayurveda, Siddha, and Unani terminology
    """
    try:
        query = {"ayush_system": {"$exists": True}}
        
        if ayush_system:
            query["ayush_system"] = ayush_system.value
        
        if traditional_name:
            query["$text"] = {"$search": traditional_name}
        
        if dosha:
            query["namaste_concepts.ayurveda_properties.doshagnata"] = dosha
        
        cursor = db.code_systems.find(query).skip(_offset).limit(_count)
        results = await cursor.to_list(length=None)
        total = await db.code_systems.count_documents(query)
        
        # Convert to Bundle
        entries = []
        db_model = CodeSystemDBModel(db.code_systems)
        
        for doc in results:
            code_system = db_model.from_dict(doc, NAMASTECodeSystem)
            if code_system:
                entry = BundleEntry(
                    fullUrl=f"{settings.fhir_base_url}/CodeSystem/{code_system.id}",
                    resource=code_system
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
        logger.error(f"Error searching NAMASTE CodeSystems: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# WHO ICD-11 specific CodeSystem endpoints
@router.get("/icd11/search", response_model=Bundle, summary="Search WHO ICD-11 CodeSystems")
async def search_icd11_code_systems(
    module: Optional[ICD11ModuleEnum] = Query(None, description="ICD-11 module filter"),
    who_version: Optional[str] = Query(None, description="WHO ICD-11 version"),
    traditional_system: Optional[str] = Query(None, description="Traditional system for TM2"),
    _count: int = Query(50, ge=1, le=1000),
    _offset: int = Query(0, ge=0),
    db=Depends(get_database),
    current_user=Depends(get_current_user)
):
    """
    Search WHO ICD-11 and TM2 CodeSystems
    Includes Biomedicine and Traditional Medicine 2 modules
    """
    try:
        query = {"icd11_module": {"$exists": True}}
        
        if module:
            query["icd11_module"] = module.value
        
        if who_version:
            query["who_version"] = who_version
        
        if traditional_system:
            query["tm2_concepts.traditional_system"] = traditional_system
        
        cursor = db.code_systems.find(query).skip(_offset).limit(_count)
        results = await cursor.to_list(length=None)
        total = await db.code_systems.count_documents(query)
        
        # Convert to Bundle
        entries = []
        db_model = CodeSystemDBModel(db.code_systems)
        
        for doc in results:
            code_system = db_model.from_dict(doc, ICD11CodeSystem)
            if code_system:
                entry = BundleEntry(
                    fullUrl=f"{settings.fhir_base_url}/CodeSystem/{code_system.id}",
                    resource=code_system
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
        logger.error(f"Error searching ICD-11 CodeSystems: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")