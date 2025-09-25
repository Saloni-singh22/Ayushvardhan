"""
NAMASTE Traditional Medicine Models
Pydantic models for Ayurveda, Unani, and Siddha medical systems
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class TraditionalMedicineSystemEnum(str, Enum):
    """Traditional medicine systems supported by NAMASTE"""
    AYURVEDA = "ayurveda"
    UNANI = "unani"
    SIDDHA = "siddha"


# Alias for backward compatibility
AyushSystemEnum = TraditionalMedicineSystemEnum


class NAMASTECodeSystem(BaseModel):
    """NAMASTE CodeSystem for traditional medicine terminologies"""
    
    # Basic identification
    system: TraditionalMedicineSystemEnum = Field(..., description="Traditional medicine system")
    code: str = Field(..., description="Unique code identifier")
    display: str = Field(..., description="Human-readable display name")
    
    # Multi-language support
    display_english: Optional[str] = Field(None, description="English translation")
    display_native: Optional[str] = Field(None, description="Native script display")
    display_transliterated: Optional[str] = Field(None, description="Transliterated display")
    
    # System-specific fields
    category: Optional[str] = Field(None, description="Category or classification")
    subcategory: Optional[str] = Field(None, description="Subcategory")
    
    # Ayurveda specific
    sanskrit_term: Optional[str] = Field(None, description="Sanskrit terminology")
    devanagari_script: Optional[str] = Field(None, description="Devanagari script")
    diacritical_marks: Optional[str] = Field(None, description="Diacritical marks")
    
    # Unani specific
    arabic_term: Optional[str] = Field(None, description="Arabic terminology")
    persian_term: Optional[str] = Field(None, description="Persian terminology")
    
    # Siddha specific
    tamil_term: Optional[str] = Field(None, description="Tamil terminology")
    tamil_script: Optional[str] = Field(None, description="Tamil script")
    
    # Common fields
    definition: Optional[str] = Field(None, description="Detailed definition")
    usage_notes: Optional[str] = Field(None, description="Usage notes and context")
    references: Optional[List[str]] = Field(None, description="Reference sources")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")
    
    class Config:
        use_enum_values = True
        validate_assignment = True


class AyurvedaConcept(NAMASTECodeSystem):
    """Ayurveda-specific concept model"""
    system: Literal[TraditionalMedicineSystemEnum.AYURVEDA] = TraditionalMedicineSystemEnum.AYURVEDA
    
    # Ayurveda-specific fields
    dosha_relation: Optional[str] = Field(None, description="Relation to Vata, Pitta, Kapha")
    rasa: Optional[str] = Field(None, description="Taste (Rasa)")
    virya: Optional[str] = Field(None, description="Potency (Virya)")
    vipaka: Optional[str] = Field(None, description="Post-digestive effect (Vipaka)")
    prabhava: Optional[str] = Field(None, description="Special effect (Prabhava)")


class UnaniConcept(NAMASTECodeSystem):
    """Unani-specific concept model"""
    system: Literal[TraditionalMedicineSystemEnum.UNANI] = TraditionalMedicineSystemEnum.UNANI
    
    # Unani-specific fields
    mizaj: Optional[str] = Field(None, description="Temperament (Mizaj)")
    quwwat: Optional[str] = Field(None, description="Potency (Quwwat)")
    afaal: Optional[str] = Field(None, description="Actions (Afaal)")


class SiddhaConcept(NAMASTECodeSystem):
    """Siddha-specific concept model"""
    system: Literal[TraditionalMedicineSystemEnum.SIDDHA] = TraditionalMedicineSystemEnum.SIDDHA
    
    # Siddha-specific fields
    suvaigal: Optional[str] = Field(None, description="Taste (Suvaigal)")
    thanmai: Optional[str] = Field(None, description="Potency (Thanmai)")
    pirivu: Optional[str] = Field(None, description="Bio-transformation (Pirivu)")


class NAMASTEConceptMap(BaseModel):
    """NAMASTE ConceptMap for traditional medicine mappings"""
    
    # Basic identification
    source_system: TraditionalMedicineSystemEnum = Field(..., description="Source traditional medicine system")
    target_system: TraditionalMedicineSystemEnum = Field(..., description="Target traditional medicine system")
    
    # Mapping details
    source_code: str = Field(..., description="Source concept code")
    target_code: str = Field(..., description="Target concept code")
    source_display: str = Field(..., description="Source display name")
    target_display: str = Field(..., description="Target display name")
    
    # Mapping relationship
    equivalence: Optional[str] = Field(None, description="Equivalence type")
    comments: Optional[str] = Field(None, description="Mapping comments")
    
    # Additional properties
    confidence_score: Optional[float] = Field(None, description="Mapping confidence score")
    verified_by: Optional[str] = Field(None, description="Verified by expert")
    verification_date: Optional[str] = Field(None, description="Verification date")
    
    class Config:
        use_enum_values = True
        validate_assignment = True


class DualCodingConcept(BaseModel):
    """Dual coding concept for traditional and modern medicine"""
    
    # Traditional medicine component
    traditional_system: TraditionalMedicineSystemEnum = Field(..., description="Traditional system")
    traditional_code: str = Field(..., description="Traditional code")
    traditional_display: str = Field(..., description="Traditional display")
    
    # Modern medicine component
    modern_system: Optional[str] = Field(None, description="Modern system (ICD-11, SNOMED, etc.)")
    modern_code: Optional[str] = Field(None, description="Modern code")
    modern_display: Optional[str] = Field(None, description="Modern display")
    
    # Mapping relationship
    relationship_type: Optional[str] = Field(None, description="Relationship type")
    mapping_confidence: Optional[float] = Field(None, description="Mapping confidence")
    
    # Clinical context
    clinical_context: Optional[str] = Field(None, description="Clinical context")
    usage_notes: Optional[str] = Field(None, description="Usage notes")
    
    class Config:
        use_enum_values = True
        validate_assignment = True


class NAMASTEValueSet(BaseModel):
    """NAMASTE ValueSet for traditional medicine concept collections"""
    
    # Basic identification
    system: TraditionalMedicineSystemEnum = Field(..., description="Traditional medicine system")
    name: str = Field(..., description="ValueSet name")
    title: str = Field(..., description="Human-readable title")
    description: Optional[str] = Field(None, description="ValueSet description")
    
    # Content
    concepts: List[NAMASTECodeSystem] = Field(..., description="Concepts included in ValueSet")
    include_all: Optional[bool] = Field(None, description="Include all concepts from system")
    
    # Filters
    filters: Optional[List[Dict[str, Any]]] = Field(None, description="Concept filters")
    
    # Metadata
    version: Optional[str] = Field(None, description="ValueSet version")
    status: Optional[str] = Field(None, description="Publication status")
    purpose: Optional[str] = Field(None, description="Purpose of ValueSet")
    
    # Usage context
    clinical_domain: Optional[str] = Field(None, description="Clinical domain")
    therapeutic_area: Optional[str] = Field(None, description="Therapeutic area")
    
    class Config:
        use_enum_values = True
        validate_assignment = True
