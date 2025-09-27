"""
Enhanced NAMASTE-WHO Multi-Tier Mapping Service
Handles the reality that most NAMASTE terms won't have direct WHO TM2 matches
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import asyncio
import logging
from datetime import datetime
from enum import Enum
from uuid import uuid4

from app.services.who_icd_client import who_icd_client, WHOICD11TM2Entity
from app.services.who_fhir_converter import who_fhir_converter
from app.database import get_database

logger = logging.getLogger(__name__)


class MappingTier(Enum):
    """Mapping confidence tiers"""
    DIRECT_TM2 = "direct_tm2"           # Direct WHO TM2 match
    BIOMEDICAL_ICD11 = "biomedical"     # WHO ICD-11 biomedical match
    SEMANTIC_BRIDGE = "semantic"        # Custom semantic grouping
    UNMAPPABLE = "unmappable"          # No suitable match found


class MappingResult:
    """Structured mapping result with confidence scoring"""
    def __init__(self, 
                 namaste_code: str,
                 namaste_display: str,
                 tier: MappingTier,
                 who_code: Optional[str] = None,
                 who_display: Optional[str] = None,
                 who_system: Optional[str] = None,
                 confidence: float = 0.0,
                 clinical_notes: Optional[str] = None,
                 search_terms_used: Optional[List[str]] = None):
        self.namaste_code = namaste_code
        self.namaste_display = namaste_display
        self.tier = tier
        self.who_code = who_code
        self.who_display = who_display
        self.who_system = who_system
        self.confidence = confidence
        self.clinical_notes = clinical_notes
        self.search_terms_used = search_terms_used or []
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "namaste_code": self.namaste_code,
            "namaste_display": self.namaste_display,
            "mapping_tier": self.tier.value,
            "who_code": self.who_code,
            "who_display": self.who_display,
            "who_system": self.who_system,
            "confidence": self.confidence,
            "clinical_notes": self.clinical_notes,
            "search_terms_used": self.search_terms_used,
            "timestamp": self.timestamp.isoformat()
        }


class EnhancedNAMASTEWHOMappingService:
    """
    Multi-tier mapping service that handles the reality of limited WHO TM2 coverage
    """
    
    def __init__(self):
        self.semantic_bridges = self._load_semantic_bridges()
        self.clinical_synonyms = self._load_clinical_synonyms()
        
    def _load_semantic_bridges(self) -> Dict[str, str]:
        """Load semantic bridge categories for unmappable terms"""
        return {
            # Dosha-related concepts
            "vata": "XK7G.0",  # Traditional medicine constitutional pattern
            "pitta": "XK7G.1", # Traditional medicine metabolic pattern  
            "kapha": "XK7G.2", # Traditional medicine structural pattern
            
            # Ayurveda-specific concepts
            "ama": "XK7G.3",     # Traditional medicine toxic accumulation
            "ojas": "XK7G.4",    # Traditional medicine vital essence
            "tejas": "XK7G.5",   # Traditional medicine metabolic fire
            "prana": "XK7G.6",   # Traditional medicine life force
            
            # Treatment modalities
            "panchakarma": "XK8Y.0",  # Traditional medicine detoxification
            "rasayana": "XK8Y.1",     # Traditional medicine rejuvenation
            "vajikarana": "XK8Y.2",   # Traditional medicine fertility therapy
        }
    
    def _load_clinical_synonyms(self) -> Dict[str, List[str]]:
        """Load clinical synonyms for better biomedical mapping"""
        return {
            # Ayurveda → Clinical terms
            "jwara": ["fever", "pyrexia", "hyperthermia", "febrile condition"],
            "shotha": ["edema", "swelling", "inflammation", "fluid retention"],
            "atisara": ["diarrhea", "loose stools", "gastroenteritis"],
            "grahani": ["irritable bowel", "malabsorption", "digestive disorder"],
            "prameha": ["diabetes", "polyuria", "metabolic disorder"],
            "kushtha": ["skin disease", "dermatitis", "eczema", "psoriasis"],
            "kasa": ["cough", "bronchitis", "respiratory disorder"],
            "shwasa": ["asthma", "dyspnea", "breathing difficulty"],
            "hridaya": ["heart disease", "cardiac disorder", "cardiovascular"],
            "unmada": ["mental disorder", "psychosis", "psychiatric condition"],
            "apasmara": ["epilepsy", "seizure disorder", "convulsions"],
            "arsha": ["hemorrhoids", "piles", "rectal disorder"],
            "mutrakrichra": ["dysuria", "urinary disorder", "UTI"],
            "raktapitta": ["bleeding disorder", "hemorrhage", "blood disorder"],
            
            # Dosha manifestations
            "vata_vikara": ["nervous disorder", "movement disorder", "neurological"],
            "pitta_vikara": ["inflammatory condition", "metabolic disorder", "liver"],
            "kapha_vikara": ["respiratory congestion", "mucus disorder", "obesity"],
        }

    async def create_enhanced_mapping(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Create comprehensive multi-tier mapping between NAMASTE and WHO systems
        """
        logger.info("Starting enhanced multi-tier NAMASTE-WHO mapping")
        
        try:
            # Get all NAMASTE terms
            namaste_terms = await self._get_namaste_terms()
            logger.info(f"Found {len(namaste_terms)} NAMASTE terms to map")
            
            # Process each term through multi-tier mapping
            mapping_results = []
            tier_stats = {tier: 0 for tier in MappingTier}
            run_id = uuid4().hex
            started_at = datetime.utcnow()
            
            for i, term in enumerate(namaste_terms):
                logger.info(f"Processing term {i+1}/{len(namaste_terms)}: {term.get('display', 'N/A')}")
                
                mapping_result = await self._map_single_term_multi_tier(term)
                mapping_results.append(mapping_result)
                tier_stats[mapping_result.tier] += 1
                
                # Rate limiting
                if i < len(namaste_terms) - 1:
                    await asyncio.sleep(0.5)
            
            # Store results and generate statistics
            await self._store_mapping_results(mapping_results)

            statistics = self._generate_mapping_statistics(mapping_results, tier_stats)
            completed_at = datetime.utcnow()
            await self._record_mapping_run(
                run_id=run_id,
                started_at=started_at,
                completed_at=completed_at,
                tier_stats=tier_stats,
                statistics=statistics,
                mapping_results=mapping_results,
                force_refresh=force_refresh,
            )
            
            logger.info("Enhanced multi-tier mapping completed successfully")
            return {
                "status": "completed",
                "total_terms": len(namaste_terms),
                "mapping_results": len(mapping_results),
                "tier_distribution": {tier.value: count for tier, count in tier_stats.items()},
                "statistics": statistics,
                "timestamp": completed_at.isoformat(),
                "run_id": run_id,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Enhanced mapping failed: {str(e)}")
            raise

    async def _map_single_term_multi_tier(self, namaste_term: Dict[str, Any]) -> MappingResult:
        """
        Map a single NAMASTE term through multiple tiers
        """
        code = namaste_term.get("code", "")
        display = namaste_term.get("display", "")
        
        # Tier 1: Try direct WHO TM2 mapping
        tm2_result = await self._try_tm2_mapping(code, display)
        if tm2_result:
            return tm2_result
        
        # Tier 2: Try biomedical ICD-11 mapping
        biomedical_result = await self._try_biomedical_mapping(code, display)
        if biomedical_result:
            return biomedical_result
        
        # Tier 3: Try semantic bridge mapping
        semantic_result = await self._try_semantic_bridge_mapping(code, display)
        if semantic_result:
            return semantic_result
        
        # Tier 4: Mark as unmappable but preserve information
        return MappingResult(
            namaste_code=code,
            namaste_display=display,
            tier=MappingTier.UNMAPPABLE,
            confidence=0.0,
            clinical_notes=f"Traditional concept '{display}' has no current WHO equivalent. Preserve for future WHO TM expansion.",
            search_terms_used=[display]
        )

    async def _try_tm2_mapping(self, code: str, display: str) -> Optional[MappingResult]:
        """Try to find direct WHO TM2 mapping"""
        try:
            # Search WHO API for TM2 entities
            search_terms = [display.lower()]
            
            # Add Sanskrit/traditional terms if available
            if any(keyword in display.lower() for keyword in ["dosha", "vata", "pitta", "kapha"]):
                search_terms.extend(["traditional medicine", "ayurveda", "constitutional"])
            
            for search_term in search_terms:
                who_response = await who_icd_client.search_entities(search_term, limit=5)
                
                # Extract entities from WHO API response
                who_entities = []
                if "destinationEntities" in who_response:
                    for entity_data in who_response["destinationEntities"]:
                        entity = WHOICD11TM2Entity(entity_data)
                        who_entities.append(entity)
                
                # Filter for TM2 entities
                tm2_entities = [entity for entity in who_entities 
                              if "tm" in entity.code.lower() or "traditional" in entity.display_title.lower()]
                
                if tm2_entities:
                    best_match = tm2_entities[0]  # Take the first/best match
                    confidence = self._calculate_confidence(display, best_match.display_title, "tm2")
                    
                    if confidence >= 0.6:  # Minimum confidence for TM2 mapping
                        return MappingResult(
                            namaste_code=code,
                            namaste_display=display,
                            tier=MappingTier.DIRECT_TM2,
                            who_code=best_match.code,
                            who_display=best_match.display_title,
                            who_system="http://id.who.int/icd/release/11/mms/tm2",
                            confidence=confidence,
                            clinical_notes=f"Direct TM2 mapping found",
                            search_terms_used=search_terms
                        )
            
            return None
            
        except Exception as e:
            logger.warning(f"TM2 mapping failed for {display}: {str(e)}")
            return None

    async def _try_biomedical_mapping(self, code: str, display: str) -> Optional[MappingResult]:
        """Try to find biomedical ICD-11 mapping using clinical synonyms"""
        try:
            # Get clinical synonyms for the term
            clinical_terms = self._get_clinical_synonyms(display)
            
            for clinical_term in clinical_terms:
                who_response = await who_icd_client.search_entities(clinical_term, limit=5)
                
                # Extract entities from WHO API response
                who_entities = []
                if "destinationEntities" in who_response:
                    for entity_data in who_response["destinationEntities"]:
                        entity = WHOICD11TM2Entity(entity_data)
                        who_entities.append(entity)
                
                # Filter out TM2 entities, focus on biomedical
                biomedical_entities = [entity for entity in who_entities 
                                     if "tm" not in entity.code.lower() and 
                                        not "traditional" in entity.display_title.lower()]
                
                if biomedical_entities:
                    best_match = biomedical_entities[0]
                    confidence = self._calculate_confidence(display, best_match.display_title, "biomedical")
                    
                    if confidence >= 0.4:  # Lower threshold for biomedical mapping
                        return MappingResult(
                            namaste_code=code,
                            namaste_display=display,
                            tier=MappingTier.BIOMEDICAL_ICD11,
                            who_code=best_match.code,
                            who_display=best_match.display_title,
                            who_system="http://id.who.int/icd/release/11/mms",
                            confidence=confidence,
                            clinical_notes=f"Biomedical equivalent mapping via clinical synonym: {clinical_term}",
                            search_terms_used=clinical_terms
                        )
            
            return None
            
        except Exception as e:
            logger.warning(f"Biomedical mapping failed for {display}: {str(e)}")
            return None

    async def _try_semantic_bridge_mapping(self, code: str, display: str) -> Optional[MappingResult]:
        """Try to create semantic bridge mapping"""
        try:
            # Check if term matches any semantic bridge categories
            for bridge_key, bridge_code in self.semantic_bridges.items():
                if bridge_key.lower() in display.lower():
                    return MappingResult(
                        namaste_code=code,
                        namaste_display=display,
                        tier=MappingTier.SEMANTIC_BRIDGE,
                        who_code=bridge_code,
                        who_display=f"Traditional medicine {bridge_key} related condition",
                        who_system="http://namaste.ayush.gov.in/fhir/CodeSystem/semantic-bridge",
                        confidence=0.4,
                        clinical_notes=f"Semantic bridge mapping to {bridge_key} category",
                        search_terms_used=[bridge_key]
                    )
            
            return None
            
        except Exception as e:
            logger.warning(f"Semantic bridge mapping failed for {display}: {str(e)}")
            return None

    def _get_clinical_synonyms(self, display: str) -> List[str]:
        """Get clinical synonyms for a traditional medicine term"""
        synonyms = []
        
        # Direct lookup
        for term, clinical_list in self.clinical_synonyms.items():
            if term.lower() in display.lower():
                synonyms.extend(clinical_list)
        
        # Add the original term
        synonyms.append(display)
        
        return list(set(synonyms))  # Remove duplicates

    def _calculate_confidence(self, namaste_term: str, who_term: str, mapping_type: str) -> float:
        """Calculate mapping confidence score"""
        # Simple text similarity for now - can be enhanced with ML models
        namaste_lower = namaste_term.lower()
        who_lower = who_term.lower()
        
        # Base confidence by mapping type
        base_confidence = {
            "tm2": 0.9,
            "biomedical": 0.6,
            "semantic": 0.3
        }.get(mapping_type, 0.1)
        
        # Adjust based on text similarity
        if namaste_lower in who_lower or who_lower in namaste_lower:
            return min(base_confidence + 0.1, 1.0)
        
        # Check for common words
        namaste_words = set(namaste_lower.split())
        who_words = set(who_lower.split())
        common_words = namaste_words.intersection(who_words)
        
        if common_words:
            similarity_boost = len(common_words) / max(len(namaste_words), len(who_words))
            return min(base_confidence + (similarity_boost * 0.2), 1.0)
        
        return base_confidence

    async def _get_namaste_terms(self) -> List[Dict[str, Any]]:
        """Extract all NAMASTE terms from existing CodeSystems"""
        try:
            db = await get_database()
            codesystems_collection = db["codesystems"]
            
            # Query for NAMASTE CodeSystems
            namaste_codesystems = codesystems_collection.find({
                "resourceType": "CodeSystem",
                "url": {"$regex": "namaste", "$options": "i"}
            })
            
            all_terms = []
            async for codesystem in namaste_codesystems:
                concepts = codesystem.get("concept", [])
                for concept in concepts:
                    all_terms.append({
                        "code": concept.get("code"),
                        "display": concept.get("display"),
                        "definition": concept.get("definition", ""),
                        "system": codesystem.get("url")
                    })
            
            logger.info(f"Extracted {len(all_terms)} NAMASTE terms from database")
            return all_terms
            
        except Exception as e:
            logger.error(f"Failed to extract NAMASTE terms: {str(e)}")
            return []

    async def _store_mapping_results(self, mapping_results: List[MappingResult]):
        """Store mapping results in database"""
        try:
            db = await get_database()
            mappings_collection = db["enhanced_mappings"]
            
            # Clear existing mappings
            await mappings_collection.delete_many({})
            
            # Store new mappings
            mapping_docs = [result.to_dict() for result in mapping_results]
            if mapping_docs:
                await mappings_collection.insert_many(mapping_docs)
            
            logger.info(f"Stored {len(mapping_docs)} mapping results")
            
        except Exception as e:
            logger.error(f"Failed to store mapping results: {str(e)}")

    async def _record_mapping_run(
        self,
        *,
        run_id: str,
        started_at: datetime,
        completed_at: datetime,
        tier_stats: Dict[MappingTier, int],
        statistics: Dict[str, Any],
        mapping_results: List[MappingResult],
        force_refresh: bool,
    ) -> None:
        """Persist run analytics for dashboard consumption."""

        try:
            db = await get_database()
            if db is None:
                return

            tier_breakdown = {tier.value: count for tier, count in tier_stats.items()}
            total_results = len(mapping_results)
            avg_confidence = (
                sum(result.confidence for result in mapping_results) / total_results
                if total_results
                else 0.0
            )
            direct_matches = tier_stats.get(MappingTier.DIRECT_TM2, 0)
            biomedical_matches = tier_stats.get(MappingTier.BIOMEDICAL_ICD11, 0)

            run_doc = {
                "job_id": run_id,
                "run_type": "enhanced_multi_tier",
                "terms_processed": total_results,
                "tier_breakdown": tier_breakdown,
                "statistics": statistics,
                "average_confidence": round(avg_confidence, 3),
                "direct_tm2_matches": direct_matches,
                "biomedical_matches": biomedical_matches,
                "force_refresh": force_refresh,
                "started_at": started_at,
                "completed_at": completed_at,
            }

            await db.mapping_runs.replace_one(
                {"job_id": run_id},
                run_doc,
                upsert=True,
            )

            metadata_doc = {
                "_id": "enhanced_namaste_who_mapping_metadata",
                "last_run_id": run_id,
                "last_started_at": started_at,
                "last_completed_at": completed_at,
                "tier_breakdown": tier_breakdown,
                "statistics": statistics,
                "average_confidence": round(avg_confidence, 3),
            }

            await db.mapping_metadata.replace_one(
                {"_id": "enhanced_namaste_who_mapping_metadata"},
                metadata_doc,
                upsert=True,
            )
        except Exception as exc:
            logger.error("Failed to store enhanced mapping analytics: %s", exc)

    def _generate_mapping_statistics(self, mapping_results: List[MappingResult], 
                                   tier_stats: Dict[MappingTier, int]) -> Dict[str, Any]:
        """Generate comprehensive mapping statistics"""
        total_terms = len(mapping_results)
        
        # Calculate coverage percentages
        coverage_stats = {}
        for tier, count in tier_stats.items():
            percentage = (count / total_terms * 100) if total_terms > 0 else 0
            coverage_stats[tier.value] = {
                "count": count,
                "percentage": round(percentage, 2)
            }
        
        # Calculate confidence distribution
        confidence_ranges = {
            "high (0.8-1.0)": 0,
            "medium (0.6-0.8)": 0,
            "low (0.4-0.6)": 0,
            "very_low (0.0-0.4)": 0
        }
        
        for result in mapping_results:
            if result.confidence >= 0.8:
                confidence_ranges["high (0.8-1.0)"] += 1
            elif result.confidence >= 0.6:
                confidence_ranges["medium (0.6-0.8)"] += 1
            elif result.confidence >= 0.4:
                confidence_ranges["low (0.4-0.6)"] += 1
            else:
                confidence_ranges["very_low (0.0-0.4)"] += 1
        
        # Insurance compatibility (terms with some WHO code)
        insurable_terms = sum(tier_stats[tier] for tier in [MappingTier.DIRECT_TM2, MappingTier.BIOMEDICAL_ICD11])
        insurance_compatibility = (insurable_terms / total_terms * 100) if total_terms > 0 else 0
        
        return {
            "total_terms_processed": total_terms,
            "tier_distribution": coverage_stats,
            "confidence_distribution": confidence_ranges,
            "insurance_compatibility_percentage": round(insurance_compatibility, 2),
            "unmappable_terms_count": tier_stats[MappingTier.UNMAPPABLE],
            "recommendations": self._generate_recommendations(tier_stats, total_terms)
        }

    def _generate_recommendations(self, tier_stats: Dict[MappingTier, int], total_terms: int) -> List[str]:
        """Generate actionable recommendations based on mapping results"""
        recommendations = []
        
        tm2_percentage = (tier_stats[MappingTier.DIRECT_TM2] / total_terms * 100) if total_terms > 0 else 0
        biomedical_percentage = (tier_stats[MappingTier.BIOMEDICAL_ICD11] / total_terms * 100) if total_terms > 0 else 0
        unmappable_percentage = (tier_stats[MappingTier.UNMAPPABLE] / total_terms * 100) if total_terms > 0 else 0
        
        if tm2_percentage < 20:
            recommendations.append("Low TM2 coverage detected. Consider expanding WHO search strategies or contributing to WHO TM2 development.")
        
        if biomedical_percentage > 60:
            recommendations.append("High biomedical mapping success. System ready for insurance integration.")
        
        if unmappable_percentage > 20:
            recommendations.append("Significant unmappable terms. Consider developing custom extension CodeSystems.")
        
        recommendations.append("Implement clinical review workflow for mapping validation.")
        recommendations.append("Consider AI/ML enhancement for improved semantic matching.")
        
        return recommendations


# Global enhanced service instance
enhanced_namaste_who_mapping_service = EnhancedNAMASTEWHOMappingService()