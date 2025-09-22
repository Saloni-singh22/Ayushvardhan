"""
NAMASTE-WHO TM2 Mapping Strategy Implementation
Optimal approach for creating FHIR-compliant dual coding system
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
import logging
from datetime import datetime

from app.services.who_icd_client import who_icd_client, WHOICD11TM2Entity
from app.services.who_fhir_converter import who_fhir_converter
from app.database import get_database

logger = logging.getLogger(__name__)


class NAMASTEWHOMappingService:
    """
    Service to create systematic mapping between NAMASTE and WHO ICD-11 TM2
    This implements the optimal architecture for dual coding
    """
    
    def __init__(self):
        self.namaste_terms_processed = 0
        self.who_matches_found = 0
        self.mapping_results = []
    
    async def create_comprehensive_mapping(self) -> Dict[str, Any]:
        """
        Phase 1: Create comprehensive NAMASTE ↔ WHO TM2 mapping
        
        Returns:
            dict: Mapping results and statistics
        """
        
        logger.info("[MAPPING] Starting comprehensive NAMASTE-WHO TM2 mapping process")
        
        # Step 1: Get all NAMASTE terms from existing CodeSystems
        namaste_terms = await self._get_namaste_terms()
        logger.info(f"[DATA] Found {len(namaste_terms)} NAMASTE terms to map")
        
        # Step 2: Search WHO API for each NAMASTE term
        who_mappings = await self._search_who_for_namaste_terms(namaste_terms)
        logger.info(f"[SEARCH] Found WHO matches for {len(who_mappings)} NAMASTE terms")
        
        # Step 3: Create enhanced WHO TM2 CodeSystem with mapped terms
        who_codesystem = await self._create_enhanced_who_codesystem(who_mappings)
        
        # Step 4: Generate FHIR ConceptMap for NAMASTE ↔ WHO TM2
        concept_map = await self._create_namaste_who_conceptmap(who_mappings)
        
        # Step 5: Store results in database
        await self._store_mapping_results(who_codesystem, concept_map, who_mappings)
        
        return {
            "namaste_terms_processed": self.namaste_terms_processed,
            "who_matches_found": self.who_matches_found,
            "mapping_success_rate": (self.who_matches_found / self.namaste_terms_processed) * 100,
            "who_codesystem_id": who_codesystem.id,
            "concept_map_id": concept_map.id,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_namaste_terms(self) -> List[Dict[str, Any]]:
        """Extract all NAMASTE terms from existing CodeSystems"""
        
        db = await get_database()
        
        # Get all NAMASTE CodeSystems by ID pattern
        namaste_codesystems = await db.codesystems.find({
            "$or": [
                {"id": {"$regex": "namaste-.*", "$options": "i"}},
                {"name": {"$regex": "NAMASTE.*", "$options": "i"}},
                {"url": {"$regex": ".*namaste.*", "$options": "i"}}
            ]
        }).to_list(None)
        
        namaste_terms = []
        
        for codesystem in namaste_codesystems:
            # Determine system type from CodeSystem ID or name
            codesystem_id = codesystem.get("id", "")
            codesystem_name = codesystem.get("name", "")
            
            system_type = "AYURVEDA"  # Default
            if "siddha" in codesystem_id.lower() or "siddha" in codesystem_name.lower():
                system_type = "SIDDHA"
            elif "unani" in codesystem_id.lower() or "unani" in codesystem_name.lower():
                system_type = "UNANI"
            elif "ayur" in codesystem_id.lower() or "ayur" in codesystem_name.lower():
                system_type = "AYURVEDA"
            
            for concept in codesystem.get("concept", []):
                namaste_terms.append({
                    "code": concept.get("code"),
                    "display": concept.get("display"),
                    "definition": concept.get("definition"),
                    "system_type": system_type,  # AYURVEDA, SIDDHA, UNANI
                    "codesystem_id": codesystem.get("id"),
                    "codesystem_url": codesystem.get("url")
                })
        
        self.namaste_terms_processed = len(namaste_terms)
        return namaste_terms
    
    async def _search_who_for_namaste_terms(self, namaste_terms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Search WHO ICD-11 API for each NAMASTE term"""
        
        mappings = []
        batch_size = 10  # Process in batches to respect rate limits
        
        for i in range(0, len(namaste_terms), batch_size):
            batch = namaste_terms[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [
                self._search_single_namaste_term(term) 
                for term in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for term, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to search WHO for '{term['display']}': {result}")
                    continue
                
                if result:  # Found WHO matches
                    mappings.append({
                        "namaste_term": term,
                        "who_entities": result,
                        "mapping_confidence": self._calculate_mapping_confidence(term, result)
                    })
                    self.who_matches_found += 1
            
            # Rate limiting delay
            await asyncio.sleep(1)
            
            logger.info(f"[PROGRESS] Processed {min(i + batch_size, len(namaste_terms))}/{len(namaste_terms)} NAMASTE terms")
        
        return mappings
    
    async def _search_single_namaste_term(self, namaste_term: Dict[str, Any]) -> Optional[List[WHOICD11TM2Entity]]:
        """Search WHO API for a single NAMASTE term"""
        
        search_terms = [
            namaste_term["display"],  # Primary term
            namaste_term["definition"][:50] if namaste_term.get("definition") else "",  # Definition excerpt
        ]
        
        # Add system-specific search terms
        system_type = namaste_term.get("system_type", "").lower()
        if system_type == "ayurveda":
            search_terms.extend(["ayurvedic", "dosha", "vata", "pitta", "kapha"])
        elif system_type == "siddha":
            search_terms.extend(["siddha", "traditional tamil"])
        elif system_type == "unani":
            search_terms.extend(["unani", "greco-arabic"])
        
        # Search WHO API with each term
        who_entities = []
        
        for search_term in search_terms:
            if not search_term or len(search_term.strip()) < 3:
                continue
                
            try:
                search_results = await who_icd_client.search_entities(
                    term=search_term.strip(),
                    limit=10,
                    include_tm2_only=True
                )
                
                entities_data = search_results.get("destinationEntities", [])
                for entity_data in entities_data:
                    entity = WHOICD11TM2Entity(entity_data)
                    if entity.is_tm2_related():
                        who_entities.append(entity)
                
                # If we found good matches, stop searching
                if len(who_entities) >= 3:
                    break
                    
            except Exception as e:
                logger.warning(f"WHO search failed for '{search_term}': {e}")
                continue
        
        return who_entities if who_entities else None
    
    def _calculate_mapping_confidence(self, namaste_term: Dict[str, Any], who_entities: List[WHOICD11TM2Entity]) -> float:
        """Calculate confidence score for NAMASTE ↔ WHO mapping"""
        
        if not who_entities:
            return 0.0
        
        namaste_display = namaste_term["display"].lower()
        max_confidence = 0.0
        
        for entity in who_entities:
            who_title = entity.display_title.lower()
            who_definition = entity.display_definition.lower()
            
            # Simple text similarity scoring
            title_match = len(set(namaste_display.split()) & set(who_title.split()))
            definition_match = len(set(namaste_display.split()) & set(who_definition.split()))
            
            confidence = (title_match * 0.7 + definition_match * 0.3) / max(len(namaste_display.split()), 1)
            max_confidence = max(max_confidence, confidence)
        
        return min(max_confidence, 1.0)
    
    async def _create_enhanced_who_codesystem(self, mappings: List[Dict[str, Any]]) -> Any:
        """Create WHO TM2 CodeSystem from mapped entities"""
        
        # Collect all unique WHO entities
        all_who_entities = []
        seen_entity_ids = set()
        
        for mapping in mappings:
            for entity in mapping["who_entities"]:
                if entity.entity_id not in seen_entity_ids:
                    all_who_entities.append(entity)
                    seen_entity_ids.add(entity.entity_id)
        
        # Create FHIR CodeSystem
        codesystem = who_fhir_converter.create_codesystem_from_entities(
            entities=all_who_entities,
            system_name="WHO-ICD11-TM2-NAMASTE-Mapped",
            system_title="WHO ICD-11 TM2 Entities Mapped from NAMASTE Terms",
            system_description="WHO ICD-11 Traditional Medicine Module 2 entities discovered through NAMASTE term mapping"
        )
        
        return codesystem
    
    async def _create_namaste_who_conceptmap(self, mappings: List[Dict[str, Any]]) -> Any:
        """Create FHIR ConceptMap for NAMASTE ↔ WHO TM2 mapping"""
        
        # This would create a proper FHIR ConceptMap resource
        # Implementation depends on your FHIR models
        
        concept_map_data = {
            "resourceType": "ConceptMap",
            "id": "namaste-who-tm2-mapping",
            "url": "http://namaste.ayush.gov.in/fhir/ConceptMap/namaste-who-tm2",
            "version": "1.0.0",
            "name": "NAMASTEWHOTMMapping",
            "title": "NAMASTE to WHO ICD-11 TM2 Concept Mapping",
            "status": "active",
            "description": "Mapping between NAMASTE traditional medicine codes and WHO ICD-11 TM2",
            "sourceUri": "http://namaste.ayush.gov.in/fhir/CodeSystem/namaste",
            "targetUri": "http://who.int/icd11/tm2",
            "group": []
        }
        
        # Group mappings by NAMASTE system type
        for mapping in mappings:
            namaste_term = mapping["namaste_term"]
            who_entities = mapping["who_entities"]
            confidence = mapping["mapping_confidence"]
            
            if confidence < 0.3:  # Skip low-confidence mappings
                continue
            
            for who_entity in who_entities[:3]:  # Top 3 matches
                concept_map_data["group"].append({
                    "source": namaste_term["codesystem_url"],
                    "target": "http://who.int/icd11/tm2",
                    "element": [{
                        "code": namaste_term["code"],
                        "display": namaste_term["display"],
                        "target": [{
                            "code": who_entity.code,
                            "display": who_entity.display_title,
                            "equivalence": "wider" if confidence > 0.7 else "inexact",
                            "comment": f"Mapping confidence: {confidence:.2f}"
                        }]
                    }]
                })
        
        return concept_map_data
    
    async def _store_mapping_results(self, who_codesystem: Any, concept_map: Any, mappings: List[Dict[str, Any]]) -> None:
        """Store mapping results in database"""
        
        db = await get_database()
        
        # Store WHO CodeSystem
        who_codesystem_dict = who_codesystem.model_dump()
        who_codesystem_dict["source"] = "WHO_ICD11_TM2_NAMASTE_MAPPED"
        who_codesystem_dict["mapping_timestamp"] = datetime.now()
        
        await db.codesystems.replace_one(
            {"id": who_codesystem.id},
            who_codesystem_dict,
            upsert=True
        )
        
        # Store ConceptMap
        concept_map["mapping_timestamp"] = datetime.now()
        await db.conceptmaps.replace_one(
            {"id": concept_map["id"]},
            concept_map,
            upsert=True
        )
        
        # Store detailed mapping metadata
        mapping_metadata = {
            "_id": "namaste_who_mapping_metadata",
            "total_namaste_terms": self.namaste_terms_processed,
            "successful_mappings": self.who_matches_found,
            "success_rate": (self.who_matches_found / self.namaste_terms_processed) * 100,
            "mapping_details": mappings,
            "created_at": datetime.now(),
            "codesystem_id": who_codesystem.id,
            "conceptmap_id": concept_map["id"]
        }
        
        await db.mapping_metadata.replace_one(
            {"_id": "namaste_who_mapping_metadata"},
            mapping_metadata,
            upsert=True
        )


# Global service instance
namaste_who_mapping_service = NAMASTEWHOMappingService()