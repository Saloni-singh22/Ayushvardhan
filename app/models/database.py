"""
Database models for MongoDB collections
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId class for Pydantic v2"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema


class CodeSystemDBModel(BaseModel):
    """Database model for CodeSystem collections"""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # FHIR R4 CodeSystem fields
    url: Optional[str] = Field(None, description="Canonical URL")
    identifier: Optional[List[Dict[str, Any]]] = Field(None, description="Additional identifiers")
    version: Optional[str] = Field(None, description="Business version")
    name: Optional[str] = Field(None, description="Name for this code system")
    title: Optional[str] = Field(None, description="Name for this code system (human friendly)")
    status: str = Field(..., description="Publication status")
    experimental: Optional[bool] = Field(None, description="For testing purposes")
    date: Optional[datetime] = Field(None, description="Date last changed")
    publisher: Optional[str] = Field(None, description="Name of the publisher")
    contact: Optional[List[Dict[str, Any]]] = Field(None, description="Contact details")
    description: Optional[str] = Field(None, description="Natural language description")
    use_context: Optional[List[Dict[str, Any]]] = Field(None, description="Use context")
    jurisdiction: Optional[List[Dict[str, Any]]] = Field(None, description="Intended jurisdiction")
    purpose: Optional[str] = Field(None, description="Why this code system is defined")
    copyright: Optional[str] = Field(None, description="Use and/or publishing restrictions")
    
    # CodeSystem specific fields
    case_sensitive: Optional[bool] = Field(None, description="If code comparison is case sensitive")
    value_set: Optional[str] = Field(None, description="Canonical reference to a value set")
    hierarchy_meaning: Optional[str] = Field(None, description="Meaning of hierarchy")
    compositional: Optional[bool] = Field(None, description="If code system defines a compositional grammar")
    version_needed: Optional[bool] = Field(None, description="If a code system version is required")
    content: str = Field(..., description="not-present | example | fragment | complete | supplement")
    supplements: Optional[str] = Field(None, description="Canonical URL of code system")
    count: Optional[int] = Field(None, description="Total concepts in the code system")
    
    # Filters and properties
    filters: Optional[List[Dict[str, Any]]] = Field(None, description="Filter definitions")
    properties: Optional[List[Dict[str, Any]]] = Field(None, description="Property definitions")
    concepts: Optional[List[Dict[str, Any]]] = Field(None, description="Concepts in the code system")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User who created this")
    
    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ConceptMapDBModel(BaseModel):
    """Database model for ConceptMap collections"""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # FHIR R4 ConceptMap fields
    url: Optional[str] = Field(None, description="Canonical URL")
    identifier: Optional[List[Dict[str, Any]]] = Field(None, description="Additional identifiers")
    version: Optional[str] = Field(None, description="Business version")
    name: Optional[str] = Field(None, description="Name for this concept map")
    title: Optional[str] = Field(None, description="Name for this concept map (human friendly)")
    status: str = Field(..., description="Publication status")
    experimental: Optional[bool] = Field(None, description="For testing purposes")
    date: Optional[datetime] = Field(None, description="Date last changed")
    publisher: Optional[str] = Field(None, description="Name of the publisher")
    contact: Optional[List[Dict[str, Any]]] = Field(None, description="Contact details")
    description: Optional[str] = Field(None, description="Natural language description")
    use_context: Optional[List[Dict[str, Any]]] = Field(None, description="Use context")
    jurisdiction: Optional[List[Dict[str, Any]]] = Field(None, description="Intended jurisdiction")
    purpose: Optional[str] = Field(None, description="Why this concept map is defined")
    copyright: Optional[str] = Field(None, description="Use and/or publishing restrictions")
    
    # ConceptMap specific fields
    source_uri: Optional[str] = Field(None, description="Source value set")
    source_canonical: Optional[str] = Field(None, description="Source canonical")
    target_uri: Optional[str] = Field(None, description="Target value set")
    target_canonical: Optional[str] = Field(None, description="Target canonical")
    groups: Optional[List[Dict[str, Any]]] = Field(None, description="Mapping groups")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User who created this")
    
    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}



class ValueSetDBModel(BaseModel):
    """Database model for ValueSet collections"""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # FHIR R4 ValueSet fields
    url: Optional[str] = Field(None, description="Canonical URL")
    identifier: Optional[List[Dict[str, Any]]] = Field(None, description="Additional identifiers")
    version: Optional[str] = Field(None, description="Business version")
    name: Optional[str] = Field(None, description="Name for this value set")
    title: Optional[str] = Field(None, description="Name for this value set (human friendly)")
    status: str = Field(..., description="Publication status")
    experimental: Optional[bool] = Field(None, description="For testing purposes")
    date: Optional[datetime] = Field(None, description="Date last changed")
    publisher: Optional[str] = Field(None, description="Name of the publisher")
    contact: Optional[List[Dict[str, Any]]] = Field(None, description="Contact details")
    description: Optional[str] = Field(None, description="Natural language description")
    use_context: Optional[List[Dict[str, Any]]] = Field(None, description="Use context")
    jurisdiction: Optional[List[Dict[str, Any]]] = Field(None, description="Intended jurisdiction")
    immutable: Optional[bool] = Field(None, description="Indicates whether or not changes can be made")
    purpose: Optional[str] = Field(None, description="Why this value set is defined")
    copyright: Optional[str] = Field(None, description="Use and/or publishing restrictions")
    
    # ValueSet composition
    compose: Optional[Dict[str, Any]] = Field(None, description="Content logical definition")
    expansion: Optional[Dict[str, Any]] = Field(None, description="Used when the value set is 'expanded'")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User who created this")
    
    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
