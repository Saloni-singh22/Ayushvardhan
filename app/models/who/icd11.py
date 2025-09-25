"""
WHO ICD-11 Models
Pydantic models for International Classification of Diseases 11th Revision
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ICD11ModuleEnum(str, Enum):
    """ICD-11 module categories"""
    MORTALITY = "mortality"
    MORBIDITY = "morbidity"
    PRIMARY_CARE = "primary_care"
    FUNCTIONING = "functioning"
    TRADITIONAL_MEDICINE = "traditional_medicine"


class ICD11CodeSystem(BaseModel):
    """ICD-11 CodeSystem for biomedical terminologies"""
    
    # Basic identification
    module: ICD11ModuleEnum = Field(..., description="ICD-11 module")
    code: str = Field(..., description="ICD-11 code identifier")
    title: str = Field(..., description="Human-readable title")
    
    # Classification details
    chapter: Optional[str] = Field(None, description="ICD-11 chapter")
    block: Optional[str] = Field(None, description="ICD-11 block")
    category: Optional[str] = Field(None, description="ICD-11 category")
    
    # Content
    definition: Optional[str] = Field(None, description="Clinical definition")
    inclusion_terms: Optional[List[str]] = Field(None, description="Inclusion terms")
    exclusion_terms: Optional[List[str]] = Field(None, description="Exclusion terms")
    
    # Coding guidance
    coding_notes: Optional[str] = Field(None, description="Coding notes")
    index_terms: Optional[List[str]] = Field(None, description="Index terms")
    
    # Relationships
    parent_codes: Optional[List[str]] = Field(None, description="Parent codes")
    child_codes: Optional[List[str]] = Field(None, description="Child codes")
    
    # Additional properties
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")
    
    class Config:
        use_enum_values = True
        validate_assignment = True


class ICD11TraditionalMedicine(ICD11CodeSystem):
    """ICD-11 Traditional Medicine section"""
    module: Literal[ICD11ModuleEnum.TRADITIONAL_MEDICINE] = ICD11ModuleEnum.TRADITIONAL_MEDICINE
    
    # Traditional medicine specific fields
    system_origin: Optional[str] = Field(None, description="Traditional system origin")
    cultural_context: Optional[str] = Field(None, description="Cultural context")


class ICD11ConceptMap(BaseModel):
    """ICD-11 ConceptMap for biomedical mappings"""
    
    # Basic identification  
    source_system: str = Field(..., description="Source terminology system")
    target_system: str = Field(..., description="Target terminology system")
    
    # Mapping details
    source_code: str = Field(..., description="Source concept code")
    target_code: str = Field(..., description="Target concept code") 
    source_display: str = Field(..., description="Source display name")
    target_display: str = Field(..., description="Target display name")
    
    # Mapping relationship
    equivalence: Optional[str] = Field(None, description="Equivalence type")
    comments: Optional[str] = Field(None, description="Mapping comments")
    
    # Validation
    validated: Optional[bool] = Field(None, description="Mapping validated")
    validator: Optional[str] = Field(None, description="Validator name")
    validation_date: Optional[str] = Field(None, description="Validation date")
    
    class Config:
        use_enum_values = True
        validate_assignment = True


class ICD11ToNAMASTEMapping(BaseModel):
    """Mapping between ICD-11 and NAMASTE traditional medicine systems"""
    
    # ICD-11 side
    icd11_code: str = Field(..., description="ICD-11 code")
    icd11_title: str = Field(..., description="ICD-11 title")
    icd11_module: ICD11ModuleEnum = Field(..., description="ICD-11 module")
    
    # NAMASTE side  
    namaste_system: str = Field(..., description="NAMASTE traditional system")
    namaste_code: str = Field(..., description="NAMASTE code")
    namaste_display: str = Field(..., description="NAMASTE display")
    
    # Mapping relationship
    mapping_type: Optional[str] = Field(None, description="Type of mapping")
    confidence_level: Optional[float] = Field(None, description="Confidence level")
    clinical_context: Optional[str] = Field(None, description="Clinical context")
    
    # Metadata
    mapped_by: Optional[str] = Field(None, description="Mapped by expert")
    mapping_date: Optional[str] = Field(None, description="Mapping date")
    reviewed: Optional[bool] = Field(None, description="Reviewed status")
    
    class Config:
        use_enum_values = True
        validate_assignment = True
