"""
WHO ICD-11 TM2 API Endpoints
FastAPI routes for retrieving and managing WHO ICD-11 TM2 data
"""

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import logging

from app.services.who_icd_client import who_icd_client, WHOICD11TM2Entity
from app.services.who_fhir_converter import who_fhir_converter
from app.models.fhir.resources import CodeSystem
from app.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/who-icd", tags=["WHO ICD-11 TM2"])


@router.get("/health", 
           summary="Check WHO API Health",
           description="Check if WHO ICD-11 API is accessible and authentication is working")
async def check_who_api_health():
    """
    Health check for WHO ICD-11 API connectivity and authentication
    
    Returns:
        dict: Health status and basic API information
    """
    try:
        # Test authentication by making a simple search
        search_result = await who_icd_client.search_entities(
            term="", 
            limit=1, 
            include_tm2_only=False
        )
        
        return {
            "status": "healthy",
            "message": "WHO ICD-11 API is accessible",
            "timestamp": datetime.now().isoformat(),
            "api_version": who_icd_client.api_version,
            "search_test": "successful"
        }
        
    except Exception as e:
        logger.error(f"WHO API health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "message": f"WHO ICD-11 API is not accessible: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )


@router.post("/search",
            summary="Search WHO ICD-11 TM2 Entities",
            description="Search for ICD-11 TM2 entities using the WHO API")
async def search_who_icd_entities(
    term: str = Query("", description="Search term (empty for all entities)"),
    limit: int = Query(30, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    tm2_only: bool = Query(True, description="Filter for Traditional Medicine entities only"),
    include_details: bool = Query(False, description="Include detailed entity information")
):
    """
    Search WHO ICD-11 entities with optional TM2 filtering
    
    Args:
        term: Search term (empty string searches all)
        limit: Number of results per page (1-100)
        offset: Pagination offset
        tm2_only: Whether to filter for TM2-related entities only
        include_details: Whether to fetch detailed information for each entity
        
    Returns:
        dict: Search results with entities and pagination info
    """
    try:
        logger.info(f"Searching WHO ICD-11 entities: '{term}', limit={limit}, offset={offset}")
        
        search_results = await who_icd_client.search_entities(
            term=term,
            limit=limit,
            offset=offset,
            include_tm2_only=tm2_only
        )
        
        entities_data = search_results.get("destinationEntities", [])
        entities = []
        
        for entity_data in entities_data:
            entity = WHOICD11TM2Entity(entity_data)
            
            entity_info = {
                "id": entity.entity_id,
                "code": entity.code,
                "title": entity.display_title,
                "uri": entity.uri,
                "is_tm2_related": entity.is_tm2_related()
            }
            
            if include_details:
                entity_info.update({
                    "definition": entity.display_definition,
                    "parent": entity.parent,
                    "child": entity.child,
                    "blockId": entity.blockId,
                    "classKind": entity.classKind,
                    "browserUrl": entity.browserUrl
                })
            
            entities.append(entity_info)
        
        return {
            "success": True,
            "search_term": term,
            "entities": entities,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(entities),
                "total_found": search_results.get("resultCount", len(entities)),
                "has_more": len(entities) == limit
            },
            "filters": {
                "tm2_only": tm2_only,
                "include_details": include_details
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error searching WHO ICD-11 entities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search WHO ICD-11 entities: {str(e)}"
        )


@router.get("/entity/{entity_id}",
           summary="Get WHO ICD-11 Entity Details",
           description="Get detailed information for a specific WHO ICD-11 entity")
async def get_who_entity_details(entity_id: str):
    """
    Get detailed information for a specific WHO ICD-11 entity
    
    Args:
        entity_id: WHO ICD-11 entity ID
        
    Returns:
        dict: Detailed entity information
    """
    try:
        logger.info(f"Fetching WHO ICD-11 entity details: {entity_id}")
        
        entity = await who_icd_client.get_entity_details(entity_id)
        
        return {
            "success": True,
            "entity": {
                "id": entity.entity_id,
                "code": entity.code,
                "title": entity.display_title,
                "definition": entity.display_definition,
                "uri": entity.uri,
                "parent": entity.parent,
                "child": entity.child,
                "inclusion": entity.inclusion,
                "exclusion": entity.exclusion,
                "codingNote": entity.codingNote,
                "blockId": entity.blockId,
                "classKind": entity.classKind,
                "browserUrl": entity.browserUrl,
                "is_tm2_related": entity.is_tm2_related(),
                "raw_data": entity.raw_data
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching WHO ICD-11 entity {entity_id}: {e}")
        raise HTTPException(
            status_code=404 if "404" in str(e) else 500,
            detail=f"Failed to get WHO ICD-11 entity: {str(e)}"
        )


@router.post("/sync/tm2",
            summary="Sync WHO ICD-11 TM2 Data",
            description="Retrieve WHO ICD-11 TM2 entities and convert to FHIR CodeSystems")
async def sync_who_tm2_data(
    background_tasks: BackgroundTasks,
    max_entities: Optional[int] = Query(None, description="Maximum entities to retrieve (None for all)"),
    batch_size: int = Query(50, ge=10, le=100, description="Batch size for retrieval"),
    save_to_database: bool = Query(True, description="Save CodeSystems to database"),
    create_by_category: bool = Query(True, description="Create separate CodeSystems by TM category")
):
    """
    Sync WHO ICD-11 TM2 data by retrieving entities and converting to FHIR CodeSystems
    This operation runs in the background due to potential long processing time
    
    Args:
        max_entities: Maximum number of entities to retrieve (None for all)
        batch_size: Number of entities to process in each batch
        save_to_database: Whether to save generated CodeSystems to database
        create_by_category: Whether to create separate CodeSystems by TM category
        
    Returns:
        dict: Sync operation status
    """
    
    # Start background task
    background_tasks.add_task(
        _sync_who_tm2_background,
        max_entities=max_entities,
        batch_size=batch_size,
        save_to_database=save_to_database,
        create_by_category=create_by_category
    )
    
    return {
        "success": True,
        "message": "WHO ICD-11 TM2 sync started in background",
        "parameters": {
            "max_entities": max_entities,
            "batch_size": batch_size,
            "save_to_database": save_to_database,
            "create_by_category": create_by_category
        },
        "timestamp": datetime.now().isoformat(),
        "note": "Check /who-icd/sync/status for progress updates"
    }


async def _sync_who_tm2_background(
    max_entities: Optional[int],
    batch_size: int,
    save_to_database: bool,
    create_by_category: bool
):
    """Background task for syncing WHO TM2 data"""
    
    try:
        logger.info(f"Starting WHO ICD-11 TM2 sync: max_entities={max_entities}, batch_size={batch_size}")
        
        # Retrieve all TM2 entities
        entities = []
        async for entity in who_icd_client.get_all_tm2_entities(
            max_entities=max_entities,
            batch_size=batch_size
        ):
            entities.append(entity)
            
            # Log progress every 50 entities
            if len(entities) % 50 == 0:
                logger.info(f"Retrieved {len(entities)} TM2 entities...")
        
        logger.info(f"Retrieved {len(entities)} total TM2 entities")
        
        if not entities:
            logger.warning("No TM2 entities found")
            return
        
        # Convert to FHIR CodeSystems
        if create_by_category:
            # Split by traditional medicine system
            categories = who_fhir_converter.split_entities_by_traditional_medicine_system(entities)
            
            for category_name, category_entities in categories.items():
                if not category_entities:
                    continue
                
                logger.info(f"Creating CodeSystem for {category_name}: {len(category_entities)} entities")
                
                code_system = who_fhir_converter.create_codesystem_by_category(
                    entities=category_entities,
                    category_name=category_name,
                    category_description=f"WHO ICD-11 Traditional Medicine entities for {category_name}"
                )
                
                if save_to_database:
                    await _save_codesystem_to_database(code_system, category_name)
        else:
            # Create single comprehensive CodeSystem
            logger.info(f"Creating comprehensive CodeSystem with {len(entities)} entities")
            
            code_system = who_fhir_converter.create_codesystem_from_entities(entities)
            
            if save_to_database:
                await _save_codesystem_to_database(code_system, "comprehensive")
        
        logger.info("WHO ICD-11 TM2 sync completed successfully")
        
    except Exception as e:
        logger.error(f"Error during WHO ICD-11 TM2 sync: {e}")


async def _save_codesystem_to_database(code_system: CodeSystem, category: str):
    """Save a CodeSystem to the database"""
    
    try:
        db = await get_database()
        
        # Convert to dict and clean for MongoDB
        code_system_dict = code_system.model_dump()
        
        # Clean language fields for text index compatibility
        def clean_for_text_index(obj):
            if isinstance(obj, dict):
                cleaned = {}
                for key, value in obj.items():
                    if key == "language" and value is None:
                        continue
                    elif key == "language" and value is not None:
                        cleaned[key] = str(value)
                    else:
                        cleaned[key] = clean_for_text_index(value)
                return cleaned
            elif isinstance(obj, list):
                return [clean_for_text_index(item) for item in obj]
            else:
                return obj
        
        code_system_dict = clean_for_text_index(code_system_dict)
        
        # Add metadata for WHO origin
        code_system_dict["source"] = "WHO_ICD11_TM2"
        code_system_dict["tm2_category"] = category
        code_system_dict["sync_timestamp"] = datetime.now()
        
        # Check if document already exists
        existing_doc = await db.codesystems.find_one(
            {"url": code_system.url, "version": code_system.version}
        )
        
        if existing_doc:
            # Update existing document
            code_system_dict.pop("_id", None)
            await db.codesystems.update_one(
                {"url": code_system.url, "version": code_system.version},
                {"$set": code_system_dict}
            )
            logger.info(f"Updated existing CodeSystem: {code_system.id}")
        else:
            # Insert new document
            code_system_dict["_id"] = code_system.id
            await db.codesystems.insert_one(code_system_dict)
            logger.info(f"Saved new CodeSystem: {code_system.id}")
        
        # Also save individual entities to who_icd_codes collection
        if code_system.concept:
            for concept in code_system.concept:
                entity_doc = {
                    "_id": f"{code_system.id}_{concept.code}",
                    "code_system_id": code_system.id,
                    "entity_id": concept.code,
                    "code": concept.code,
                    "title": {"@value": concept.display},
                    "definition": {"@value": concept.definition} if concept.definition else None,
                    "uri": f"{code_system.url}#{concept.code}",
                    "source": "WHO_ICD11_TM2",
                    "tm2_category": category,
                    "sync_timestamp": datetime.now(),
                    "release": "2023-01",
                    "linearization": "mms"
                }
                
                # Add properties
                if concept.property:
                    for prop in concept.property:
                        if prop.get("code") == "parentId":
                            entity_doc["parent"] = [prop.get("valueString")]
                        elif prop.get("code") == "browserUrl":
                            entity_doc["browserUrl"] = prop.get("valueString")
                        elif prop.get("code") == "blockId":
                            entity_doc["blockId"] = prop.get("valueString")
                        elif prop.get("code") == "classKind":
                            entity_doc["classKind"] = prop.get("valueString")
                
                # Upsert individual entity
                await db.who_icd_codes.replace_one(
                    {"entity_id": concept.code, "code_system_id": code_system.id},
                    entity_doc,
                    upsert=True
                )
        
        logger.info(f"Saved CodeSystem and {len(code_system.concept or [])} entities for {category}")
        
    except Exception as e:
        logger.error(f"Error saving CodeSystem to database: {e}")


@router.get("/search/keywords",
           summary="Search TM2 by Keywords",
           description="Search for TM2 entities using predefined keywords")
async def search_tm2_by_keywords(
    keywords: str = Query(..., description="Comma-separated keywords to search for"),
    save_to_database: bool = Query(False, description="Save found entities to database")
):
    """
    Search for TM2 entities using specific keywords
    
    Args:
        keywords: Comma-separated list of keywords
        save_to_database: Whether to save found entities to database
        
    Returns:
        dict: Found entities grouped by keyword
    """
    try:
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        
        if not keyword_list:
            raise HTTPException(status_code=400, detail="No valid keywords provided")
        
        logger.info(f"Searching TM2 entities for keywords: {keyword_list}")
        
        entities = await who_icd_client.search_tm2_by_keywords(keyword_list)
        
        # Group entities by keyword match
        keyword_groups = {}
        for keyword in keyword_list:
            matching_entities = []
            for entity in entities:
                if (keyword.lower() in entity.display_title.lower() or 
                    keyword.lower() in entity.display_definition.lower()):
                    matching_entities.append({
                        "id": entity.entity_id,
                        "code": entity.code,
                        "title": entity.display_title,
                        "definition": entity.display_definition,
                        "uri": entity.uri
                    })
            keyword_groups[keyword] = matching_entities
        
        if save_to_database and entities:
            # Convert to CodeSystem and save
            code_system = who_fhir_converter.create_codesystem_from_entities(
                entities=entities,
                system_name=f"ICD-11-TM2-Keywords-{datetime.now().strftime('%Y%m%d')}",
                system_title="ICD-11 TM2 Entities Found by Keywords",
                system_description=f"WHO ICD-11 TM2 entities found using keywords: {', '.join(keyword_list)}"
            )
            
            await _save_codesystem_to_database(code_system, "keyword_search")
        
        return {
            "success": True,
            "keywords_searched": keyword_list,
            "total_entities_found": len(entities),
            "entities_by_keyword": keyword_groups,
            "saved_to_database": save_to_database,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error searching TM2 by keywords: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search TM2 by keywords: {str(e)}"
        )


@router.get("/codesystems",
           summary="List WHO TM2 CodeSystems",
           description="List FHIR CodeSystems created from WHO ICD-11 TM2 data")
async def list_who_tm2_codesystems():
    """
    List all FHIR CodeSystems created from WHO ICD-11 TM2 data
    
    Returns:
        dict: List of WHO TM2 CodeSystems
    """
    try:
        db = await get_database()
        
        # Find all CodeSystems from WHO ICD-11 TM2
        cursor = db.codesystems.find(
            {"source": "WHO_ICD11_TM2"},
            {
                "_id": 1,
                "id": 1,
                "url": 1,
                "version": 1,
                "name": 1,
                "title": 1,
                "description": 1,
                "count": 1,
                "tm2_category": 1,
                "sync_timestamp": 1,
                "status": 1
            }
        )
        
        codesystems = await cursor.to_list(None)
        
        return {
            "success": True,
            "codesystems": codesystems,
            "total_count": len(codesystems),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing WHO TM2 CodeSystems: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list WHO TM2 CodeSystems: {str(e)}"
        )