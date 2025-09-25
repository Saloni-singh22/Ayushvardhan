"""
Base FHIR R4 models and common data types
Foundation classes for all FHIR resources with proper validation
"""

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
import re


class FHIRBase(BaseModel):
    """Base class for all FHIR resources"""
    
    class Config:
        extra = "allow"  # Allow additional fields for flexibility
        validate_assignment = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DomainResource(FHIRBase):
    """Base class for FHIR domain resources"""
    id: Optional[str] = Field(None, description="Logical id of this artifact")
    meta: Optional[Dict[str, Any]] = Field(None, description="Metadata about the resource")
    implicitRules: Optional[str] = Field(None, description="A set of rules under which this content was created")
    language: Optional[str] = Field(None, description="Language of the resource content")
    text: Optional[Dict[str, Any]] = Field(None, description="Text summary of the resource")
    contained: Optional[List[Dict[str, Any]]] = Field(None, description="Contained, inline Resources")
    extension: Optional[List[Dict[str, Any]]] = Field(None, description="Additional content defined by implementations")
    modifierExtension: Optional[List[Dict[str, Any]]] = Field(None, description="Extensions that cannot be ignored")


class ResourceTypeEnum(str, Enum):
    """FHIR resource types supported by the terminology service"""
    CODESYSTEM = "CodeSystem"
    CONCEPTMAP = "ConceptMap"
    VALUESET = "ValueSet"
    BUNDLE = "Bundle"
    OPERATIONOUTCOME = "OperationOutcome"
    PARAMETERS = "Parameters"


class PublicationStatusEnum(str, Enum):
    """FHIR publication status values"""
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"
    UNKNOWN = "unknown"


class BundleTypeEnum(str, Enum):
    """FHIR Bundle types"""
    DOCUMENT = "document"
    MESSAGE = "message"
    TRANSACTION = "transaction"
    TRANSACTION_RESPONSE = "transaction-response"
    BATCH = "batch"
    BATCH_RESPONSE = "batch-response"
    HISTORY = "history"
    SEARCHSET = "searchset"
    COLLECTION = "collection"


class ConceptMapEquivalenceEnum(str, Enum):
    """ConceptMap equivalence values"""
    RELATEDTO = "relatedto"
    EQUIVALENT = "equivalent"
    EQUAL = "equal"
    WIDER = "wider"
    SUBSUMES = "subsumes"
    NARROWER = "narrower"
    SPECIALIZES = "specializes"
    INEXACT = "inexact"
    UNMATCHED = "unmatched"
    DISJOINT = "disjoint"


class Identifier(FHIRBase):
    """FHIR Identifier data type"""
    use: Optional[str] = Field(None, pattern="^(usual|official|temp|secondary|old)$")
    type: Optional[Dict[str, Any]] = None
    system: Optional[str] = Field(None, description="Namespace for the identifier value")
    value: Optional[str] = Field(None, description="The identifier value")
    period: Optional[Dict[str, Any]] = None
    assigner: Optional[Dict[str, Any]] = None


class Coding(FHIRBase):
    """FHIR Coding data type"""
    system: Optional[str] = Field(None, description="Identity of the terminology system")
    version: Optional[str] = Field(None, description="Version of the system")
    code: Optional[str] = Field(None, description="Symbol in syntax defined by the system")
    display: Optional[str] = Field(None, description="Representation defined by the system")
    userSelected: Optional[bool] = Field(None, description="If this coding was chosen directly by the user")


class CodeableConcept(FHIRBase):
    """FHIR CodeableConcept data type"""
    coding: Optional[List[Coding]] = Field(None, description="Code defined by a terminology system")
    text: Optional[str] = Field(None, description="Plain text representation of the concept")


class ContactDetail(FHIRBase):
    """FHIR ContactDetail data type"""
    name: Optional[str] = Field(None, description="Name of contact")
    telecom: Optional[List[Dict[str, Any]]] = Field(None, description="Contact details")


class UsageContext(FHIRBase):
    """FHIR UsageContext data type"""
    code: Coding = Field(..., description="Type of context being specified")
    value: Union[CodeableConcept, Dict[str, Any]] = Field(..., description="Value that defines the context")


class Reference(FHIRBase):
    """FHIR Reference data type"""
    reference: Optional[str] = Field(None, description="Literal reference, Relative, internal or absolute URL")
    type: Optional[str] = Field(None, description="Type the reference refers to")
    identifier: Optional[Identifier] = Field(None, description="Logical reference, when literal reference is not known")
    display: Optional[str] = Field(None, description="Text alternative for the resource")


class Period(FHIRBase):
    """FHIR Period data type"""
    start: Optional[datetime] = Field(None, description="Starting time with inclusive boundary")
    end: Optional[datetime] = Field(None, description="End time with inclusive boundary")


class Extension(FHIRBase):
    """FHIR Extension data type"""
    url: str = Field(..., description="Identifies the meaning of the extension")
    value: Optional[Union[str, int, bool, Dict[str, Any]]] = Field(None, description="Value of extension")


def validate_uri(uri: str) -> bool:
    """Validate URI format"""
    if not uri:
        return False
    # Basic URI validation
    uri_pattern = re.compile(
        r'^[a-zA-Z][a-zA-Z0-9+.-]*:'  # scheme
        r'[^\s]*$'  # rest of URI
    )
    return bool(uri_pattern.match(uri))


def validate_canonical(canonical: str) -> bool:
    """Validate canonical URL format"""
    if not canonical:
        return False
    # Basic URL validation for canonical URLs
    url_pattern = re.compile(
        r'^https?://'  # http or https
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(canonical))
