"""
WHO ICD-11 TM2 to FHIR CodeSystem Converter
Transforms WHO ICD-11 TM2 entities into FHIR R4 compliant CodeSystem resources
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from app.models.fhir.resources import CodeSystem, CodeSystemConcept, CodeSystemProperty
from app.models.fhir.base import PublicationStatusEnum, ContactDetail
from app.services.who_icd_client import WHOICD11TM2Entity

logger = logging.getLogger(__name__)


class WHOICDToFHIRConverter:
    """
    Converter for transforming WHO ICD-11 TM2 entities to FHIR CodeSystem resources
    """
    
    def __init__(self):
        self.base_url = "http://id.who.int/icd/release/11/mms"
        self.publisher = "World Health Organization"
        self.copyright = "© World Health Organization. All rights reserved."
    
    def create_codesystem_from_entities(
        self, 
        entities: List[WHOICD11TM2Entity],
        system_name: str = "ICD-11-TM2",
        system_title: str = "ICD-11 Traditional Medicine Chapter 2",
        system_description: str = "WHO ICD-11 Traditional Medicine conditions, Module 2"
    ) -> CodeSystem:
        """
        Create a FHIR CodeSystem from a list of WHO ICD-11 TM2 entities
        
        Args:
            entities: List of WHO ICD-11 TM2 entities
            system_name: Computer-friendly name for the CodeSystem
            system_title: Human-friendly title
            system_description: Description of the CodeSystem
            
        Returns:
            CodeSystem: FHIR R4 compliant CodeSystem
        """
        logger.info(f"Creating FHIR CodeSystem from {len(entities)} WHO ICD-11 TM2 entities")
        
        # Generate CodeSystem metadata
        code_system_id = f"who-icd-11-tm2-{datetime.now().strftime('%Y%m%d')}"
        url = f"{self.base_url}/CodeSystem/{code_system_id}"
        version = f"ICD-11-{datetime.now().strftime('%Y.%m')}"
        
        # Create concepts from entities
        concepts = []
        for entity in entities:
            concept = self._entity_to_concept(entity)
            if concept:
                concepts.append(concept)
        
        # Define properties used in concepts
        properties = [
            CodeSystemProperty(
                code="definition",
                description="Official WHO definition of the concept",
                type="string"
            ),
            CodeSystemProperty(
                code="inclusion",
                description="Inclusion criteria for the concept",
                type="string"
            ),
            CodeSystemProperty(
                code="exclusion", 
                description="Exclusion criteria for the concept",
                type="string"
            ),
            CodeSystemProperty(
                code="codingNote",
                description="Coding notes and guidance",
                type="string"
            ),
            CodeSystemProperty(
                code="blockId",
                description="ICD-11 block identifier",
                type="string"
            ),
            CodeSystemProperty(
                code="classKind",
                description="ICD-11 class kind",
                type="string"
            ),
            CodeSystemProperty(
                code="browserUrl",
                description="WHO ICD-11 browser URL",
                type="string"
            ),
            CodeSystemProperty(
                code="parentId",
                description="Parent concept identifier",
                type="string"
            )
        ]
        
        # Create contact information
        contact = [
            ContactDetail(
                name="World Health Organization",
                telecom=[{
                    "system": "url",
                    "value": "https://www.who.int/standards/classifications"
                }]
            )
        ]
        
        # Create the CodeSystem
        code_system = CodeSystem(
            id=code_system_id,
            url=url,
            version=version,
            name=system_name,
            title=system_title,
            status=PublicationStatusEnum.ACTIVE,
            experimental=False,
            date=datetime.now(),
            publisher=self.publisher,
            contact=contact,
            description=system_description,
            copyright=self.copyright,
            caseSensitive=True,
            content="complete",
            count=len(concepts),
            property=properties,
            concept=concepts
        )
        
        logger.info(f"Created FHIR CodeSystem '{code_system_id}' with {len(concepts)} concepts")
        return code_system
    
    def _entity_to_concept(self, entity: WHOICD11TM2Entity) -> Optional[CodeSystemConcept]:
        """
        Convert a WHO ICD-11 TM2 entity to a FHIR CodeSystem concept
        
        Args:
            entity: WHO ICD-11 TM2 entity
            
        Returns:
            CodeSystemConcept: FHIR concept or None if conversion fails
        """
        try:
            # Extract code from entity
            code = entity.code or entity.entity_id
            if not code:
                logger.warning(f"Entity has no code: {entity.uri}")
                return None
            
            # Clean up code (remove any prefixes/suffixes)
            if "/" in code:
                code = code.split("/")[-1]
            
            # Create basic concept
            concept = CodeSystemConcept(
                code=code,
                display=entity.display_title,
                definition=entity.display_definition if entity.display_definition else None
            )
            
            # Add properties
            properties = []
            
            # Definition property
            if entity.display_definition:
                properties.append({
                    "code": "definition",
                    "valueString": entity.display_definition
                })
            
            # Inclusion criteria
            if entity.inclusion:
                inclusion_text = self._extract_text_from_multilingual(entity.inclusion)
                if inclusion_text:
                    properties.append({
                        "code": "inclusion",
                        "valueString": inclusion_text
                    })
            
            # Exclusion criteria
            if entity.exclusion:
                exclusion_text = self._extract_text_from_multilingual(entity.exclusion)
                if exclusion_text:
                    properties.append({
                        "code": "exclusion",
                        "valueString": exclusion_text
                    })
            
            # Coding note
            if entity.codingNote:
                coding_note_text = self._extract_text_from_multilingual(entity.codingNote)
                if coding_note_text:
                    properties.append({
                        "code": "codingNote",
                        "valueString": coding_note_text
                    })
            
            # Block ID
            if entity.blockId:
                properties.append({
                    "code": "blockId",
                    "valueString": entity.blockId
                })
            
            # Class kind
            if entity.classKind:
                properties.append({
                    "code": "classKind",
                    "valueString": entity.classKind
                })
            
            # Browser URL
            if entity.browserUrl:
                properties.append({
                    "code": "browserUrl",
                    "valueString": entity.browserUrl
                })
            
            # Parent information
            if entity.parent:
                # Take the first parent if multiple
                parent_uri = entity.parent[0] if isinstance(entity.parent, list) else entity.parent
                if isinstance(parent_uri, str):
                    parent_id = parent_uri.split("/")[-1] if "/" in parent_uri else parent_uri
                    properties.append({
                        "code": "parentId",
                        "valueString": parent_id
                    })
            
            concept.property = properties if properties else None
            
            return concept
            
        except Exception as e:
            logger.error(f"Failed to convert entity to concept: {entity.uri}, error: {e}")
            return None
    
    def _extract_text_from_multilingual(self, multilingual_field: Any) -> Optional[str]:
        """
        Extract English text from multilingual WHO API field
        
        Args:
            multilingual_field: WHO API multilingual field (dict or string)
            
        Returns:
            str: Extracted text or None
        """
        if not multilingual_field:
            return None
        
        if isinstance(multilingual_field, str):
            return multilingual_field
        
        if isinstance(multilingual_field, dict):
            # Try various English keys
            for key in ["@value", "en", "en-US", "en-GB"]:
                if key in multilingual_field and multilingual_field[key]:
                    return multilingual_field[key]
            
            # If no English, try any value
            if multilingual_field:
                values = [v for v in multilingual_field.values() if v]
                return values[0] if values else None
        
        return None
    
    def create_codesystem_by_category(
        self, 
        entities: List[WHOICD11TM2Entity],
        category_name: str,
        category_description: str
    ) -> CodeSystem:
        """
        Create a FHIR CodeSystem for a specific category of TM2 entities
        
        Args:
            entities: List of WHO ICD-11 TM2 entities in this category
            category_name: Category name (e.g., "Ayurveda", "TCM")
            category_description: Description of the category
            
        Returns:
            CodeSystem: FHIR R4 compliant CodeSystem for the category
        """
        system_name = f"ICD-11-TM2-{category_name.replace(' ', '-')}"
        system_title = f"ICD-11 Traditional Medicine - {category_name}"
        system_description = f"WHO ICD-11 Traditional Medicine conditions for {category_name}. {category_description}"
        
        return self.create_codesystem_from_entities(
            entities=entities,
            system_name=system_name,
            system_title=system_title,
            system_description=system_description
        )
    
    def split_entities_by_traditional_medicine_system(
        self, 
        entities: List[WHOICD11TM2Entity]
    ) -> Dict[str, List[WHOICD11TM2Entity]]:
        """
        Split entities by traditional medicine system based on keywords
        
        Args:
            entities: List of WHO ICD-11 TM2 entities
            
        Returns:
            dict: Entities grouped by traditional medicine system
        """
        categories = {
            "Ayurveda": [],
            "Traditional Chinese Medicine": [],
            "Unani": [],
            "Siddha": [],
            "Homeopathy": [],
            "Naturopathy": [],
            "Acupuncture": [],
            "General Traditional Medicine": []
        }
        
        # Keywords for each category
        category_keywords = {
            "Ayurveda": ["ayurveda", "ayurvedic", "dosha", "vata", "pitta", "kapha"],
            "Traditional Chinese Medicine": ["chinese medicine", "tcm", "qi", "meridian", "acupuncture"],
            "Unani": ["unani", "yunani", "tibb", "mizaj"],
            "Siddha": ["siddha", "tamil", "dravidian"],
            "Homeopathy": ["homeopathy", "homeopathic", "potentization"],
            "Naturopathy": ["naturopathy", "naturopathic", "natural healing"],
            "Acupuncture": ["acupuncture", "acupressure", "needle", "meridian"]
        }
        
        for entity in entities:
            title_lower = entity.display_title.lower()
            definition_lower = entity.display_definition.lower()
            
            categorized = False
            
            # Check each category
            for category, keywords in category_keywords.items():
                if any(keyword in title_lower or keyword in definition_lower for keyword in keywords):
                    categories[category].append(entity)
                    categorized = True
                    break
            
            # If not categorized, put in general
            if not categorized:
                categories["General Traditional Medicine"].append(entity)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}


# Global instance
who_fhir_converter = WHOICDToFHIRConverter()