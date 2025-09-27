"""
FHIR R4 resource models for terminology services
Implements CodeSystem, ConceptMap, ValueSet, and Bundle resources
"""

from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime
from pydantic import Field, field_validator, model_validator

from .base import (
    DomainResource, 
    ResourceTypeEnum, 
    PublicationStatusEnum, 
    BundleTypeEnum,
    ConceptMapEquivalenceEnum,
    Identifier,
    Coding,
    CodeableConcept,
    ContactDetail,
    UsageContext,
    Reference,
    Period,
    Extension,
    validate_uri,
    validate_canonical
)


class ParametersParameterPart(DomainResource):
    """Nested part element inside a FHIR Parameters.parameter."""

    name: str = Field(..., description="Name of additional parameter part")
    valueBoolean: Optional[bool] = Field(None, description="Boolean parameter value")
    valueCode: Optional[str] = Field(None, description="Code parameter value")
    valueString: Optional[str] = Field(None, description="String parameter value")
    valueUri: Optional[str] = Field(None, description="URI parameter value")
    valueCoding: Optional[Coding] = Field(None, description="Coding parameter value")
    valueInteger: Optional[int] = Field(None, description="Integer parameter value")
    valueDecimal: Optional[float] = Field(None, description="Decimal parameter value")
    valueDateTime: Optional[datetime] = Field(None, description="DateTime parameter value")
    resource: Optional[DomainResource] = Field(None, description="Inline resource payload")
    part: Optional[List['ParametersParameterPart']] = Field(
        None,
        description="Further nested parameter parts"
    )


class ParametersParameter(DomainResource):
    """Top-level parameter element in a FHIR Parameters resource."""

    name: str = Field(..., description="Name of the parameter")
    valueBoolean: Optional[bool] = Field(None, description="Boolean parameter value")
    valueCode: Optional[str] = Field(None, description="Code parameter value")
    valueString: Optional[str] = Field(None, description="String parameter value")
    valueUri: Optional[str] = Field(None, description="URI parameter value")
    valueCoding: Optional[Coding] = Field(None, description="Coding parameter value")
    valueInteger: Optional[int] = Field(None, description="Integer parameter value")
    valueDecimal: Optional[float] = Field(None, description="Decimal parameter value")
    valueDateTime: Optional[datetime] = Field(None, description="DateTime parameter value")
    resource: Optional[DomainResource] = Field(None, description="Inline resource payload")
    part: Optional[List[ParametersParameterPart]] = Field(
        None,
        description="Nested parameter parts"
    )


class Parameters(DomainResource):
    """FHIR Parameters resource used for custom operation responses."""

    resourceType: Literal["Parameters"] = Field(default="Parameters")
    parameter: List[ParametersParameter] = Field(
        default_factory=list,
        description="Operation response parameters"
    )


class CodeSystemProperty(DomainResource):
    """CodeSystem property definition"""
    code: str = Field(..., description="Identifies the property on the concepts")
    uri: Optional[str] = Field(None, description="Formal identifier for the property")
    description: Optional[str] = Field(None, description="Why the property is defined")
    type: str = Field(..., pattern="^(code|Coding|string|integer|boolean|dateTime|decimal)$")


class CodeSystemConcept(DomainResource):
    """CodeSystem concept definition"""
    code: str = Field(..., description="Code that identifies concept")
    display: Optional[str] = Field(None, description="Text to display to the user")
    definition: Optional[str] = Field(None, description="Formal definition")
    designation: Optional[List[Dict[str, Any]]] = Field(None, description="Additional representations for the concept")
    property: Optional[List[Dict[str, Any]]] = Field(None, description="Property value for the concept")
    concept: Optional[List['CodeSystemConcept']] = Field(None, description="Child Concepts (is-a/contains/categorizes)")


class CodeSystemFilter(DomainResource):
    """CodeSystem filter definition"""
    code: str = Field(..., description="Code that identifies the filter")
    description: Optional[str] = Field(None, description="How or why the filter is used")
    operator: List[str] = Field(..., description="Operators that can be used with filter")
    value: str = Field(..., description="What to use for the value")


class CodeSystem(DomainResource):
    """FHIR R4 CodeSystem resource for NAMASTE and biomedical terminologies"""
    
    resourceType: Literal["CodeSystem"] = Field(default="CodeSystem")
    
    # Required elements
    url: Optional[str] = Field(None, description="Canonical identifier for this code system")
    identifier: Optional[List[Identifier]] = Field(None, description="Additional identifiers")
    version: Optional[str] = Field(None, description="Business version of the code system")
    name: Optional[str] = Field(None, description="Name for this code system (computer friendly)")
    title: Optional[str] = Field(None, description="Name for this code system (human friendly)")
    status: PublicationStatusEnum = Field(..., description="Publication status")
    experimental: Optional[bool] = Field(None, description="For testing purposes, not real usage")
    date: Optional[datetime] = Field(None, description="Date last changed")
    publisher: Optional[str] = Field(None, description="Name of the publisher")
    contact: Optional[List[ContactDetail]] = Field(None, description="Contact details for the publisher")
    description: Optional[str] = Field(None, description="Natural language description")
    useContext: Optional[List[UsageContext]] = Field(None, description="Context the content is intended to support")
    jurisdiction: Optional[List[CodeableConcept]] = Field(None, description="Intended jurisdiction")
    
    # CodeSystem specific elements
    purpose: Optional[str] = Field(None, description="Why this code system is defined")
    copyright: Optional[str] = Field(None, description="Use and/or publishing restrictions")
    caseSensitive: Optional[bool] = Field(None, description="If code comparison is case sensitive")
    valueSet: Optional[str] = Field(None, description="Canonical reference to the value set")
    hierarchyMeaning: Optional[str] = Field(None, pattern="^(grouped-by|is-a|part-of|classified-with)$")
    compositional: Optional[bool] = Field(None, description="If code system defines a compositional grammar")
    versionNeeded: Optional[bool] = Field(None, description="If definitions are not stable")
    content: str = Field(..., pattern="^(not-present|example|fragment|complete|supplement)$")
    supplements: Optional[str] = Field(None, description="Canonical URL of Code System this adds to")
    count: Optional[int] = Field(None, description="Total concepts in the code system")
    
    # Filters and properties
    filter: Optional[List[CodeSystemFilter]] = Field(None, description="Filter that can be used in a value set")
    property: Optional[List[CodeSystemProperty]] = Field(None, description="Additional information supplied about each concept")
    concept: Optional[List[CodeSystemConcept]] = Field(None, description="Concepts in the code system")
    
    @field_validator('url')
    def validate_url(cls, v):
        if v and not validate_canonical(v):
            raise ValueError('Invalid canonical URL format')
        return v
    
    @field_validator('valueSet')
    def validate_valueset_url(cls, v):
        if v and not validate_canonical(v):
            raise ValueError('Invalid ValueSet canonical URL format')
        return v
    
    @field_validator('supplements')
    def validate_supplements_url(cls, v):
        if v and not validate_canonical(v):
            raise ValueError('Invalid supplements canonical URL format')
        return v


class ConceptMapGroup(DomainResource):
    """ConceptMap group of mappings"""
    source: Optional[str] = Field(None, description="Source system where concepts to be mapped are defined")
    sourceVersion: Optional[str] = Field(None, description="Specific version of the code system")
    target: Optional[str] = Field(None, description="Target system that the concepts are to be mapped to")
    targetVersion: Optional[str] = Field(None, description="Specific version of the target code system")
    element: List['ConceptMapElement'] = Field(..., description="Mappings for a concept from the source set")
    unmapped: Optional[Dict[str, Any]] = Field(None, description="What to do when there is no mapping")


class ConceptMapElement(DomainResource):
    """ConceptMap source element"""
    code: Optional[str] = Field(None, description="Identifies element being mapped")
    display: Optional[str] = Field(None, description="Display for the code")
    target: Optional[List['ConceptMapTarget']] = Field(None, description="Concept in target system for this concept")


class ConceptMapTarget(DomainResource):
    """ConceptMap target element"""
    code: Optional[str] = Field(None, description="Code that identifies the target element")
    display: Optional[str] = Field(None, description="Display for the code")
    equivalence: ConceptMapEquivalenceEnum = Field(..., description="Relationship between source and target concepts")
    comment: Optional[str] = Field(None, description="Description of status/issues in mapping")
    dependsOn: Optional[List[Dict[str, Any]]] = Field(None, description="Other elements required for this mapping")
    product: Optional[List[Dict[str, Any]]] = Field(None, description="Other concepts that this mapping also produces")


class ConceptMap(DomainResource):
    """FHIR R4 ConceptMap resource for NAMASTE to ICD-11 mappings"""
    
    resourceType: Literal["ConceptMap"] = Field(default="ConceptMap")
    
    # Required elements
    url: Optional[str] = Field(None, description="Canonical identifier for this concept map")
    identifier: Optional[List[Identifier]] = Field(None, description="Additional identifiers")
    version: Optional[str] = Field(None, description="Business version of the concept map")
    name: Optional[str] = Field(None, description="Name for this concept map (computer friendly)")
    title: Optional[str] = Field(None, description="Name for this concept map (human friendly)")
    status: PublicationStatusEnum = Field(..., description="Publication status")
    experimental: Optional[bool] = Field(None, description="For testing purposes, not real usage")
    date: Optional[datetime] = Field(None, description="Date last changed")
    publisher: Optional[str] = Field(None, description="Name of the publisher")
    contact: Optional[List[ContactDetail]] = Field(None, description="Contact details for the publisher")
    description: Optional[str] = Field(None, description="Natural language description")
    useContext: Optional[List[UsageContext]] = Field(None, description="Context the content is intended to support")
    jurisdiction: Optional[List[CodeableConcept]] = Field(None, description="Intended jurisdiction")
    
    # ConceptMap specific elements
    purpose: Optional[str] = Field(None, description="Why this concept map is defined")
    copyright: Optional[str] = Field(None, description="Use and/or publishing restrictions")
    
    # Source and target
    source: Optional[Union[str, Reference]] = Field(None, description="Source value set")
    target: Optional[Union[str, Reference]] = Field(None, description="Target value set")
    
    # Groups of mappings
    group: Optional[List[ConceptMapGroup]] = Field(None, description="Same source and target systems")
    
    @field_validator('url')
    def validate_url(cls, v):
        if v and not validate_canonical(v):
            raise ValueError('Invalid canonical URL format')
        return v


class ValueSetCompose(DomainResource):
    """ValueSet compose definition"""
    lockedDate: Optional[str] = Field(None, description="Fixed date for references with no version")
    inactive: Optional[bool] = Field(None, description="Whether inactive codes are allowed")
    include: List['ValueSetInclude'] = Field(..., description="Include one or more codes from a code system or other value set")
    exclude: Optional[List['ValueSetInclude']] = Field(None, description="Explicitly exclude codes")


class ValueSetInclude(DomainResource):
    """ValueSet include/exclude definition"""
    system: Optional[str] = Field(None, description="The system the codes come from")
    version: Optional[str] = Field(None, description="Specific version of the code system")
    concept: Optional[List[Dict[str, Any]]] = Field(None, description="A concept defined in the system")
    filter: Optional[List[Dict[str, Any]]] = Field(None, description="Select codes/concepts by their properties")
    valueSet: Optional[List[str]] = Field(None, description="Select the contents included in this value set")


class ValueSetExpansion(DomainResource):
    """ValueSet expansion definition"""
    identifier: Optional[str] = Field(None, description="Identifies the value set expansion")
    timestamp: datetime = Field(..., description="Time ValueSet expansion happened")
    total: Optional[int] = Field(None, description="Total number of codes in the expansion")
    offset: Optional[int] = Field(None, description="Offset at which this resource starts")
    parameter: Optional[List[Dict[str, Any]]] = Field(None, description="Parameter that controlled the expansion process")
    contains: Optional[List['ValueSetExpansionContains']] = Field(None, description="Codes in the value set")


class ValueSetExpansionContains(DomainResource):
    """ValueSet expansion contains"""
    system: Optional[str] = Field(None, description="System value for the code")
    abstract: Optional[bool] = Field(None, description="If user cannot select this entry")
    inactive: Optional[bool] = Field(None, description="If concept is inactive in the code system")
    version: Optional[str] = Field(None, description="Version in which this code/display is defined")
    code: Optional[str] = Field(None, description="Code - if blank, this is not a selectable code")
    display: Optional[str] = Field(None, description="User display for the concept")
    designation: Optional[List[Dict[str, Any]]] = Field(None, description="Additional representations for this item")
    contains: Optional[List['ValueSetExpansionContains']] = Field(None, description="Codes contained under this entry")


class ValueSet(DomainResource):
    """FHIR R4 ValueSet resource for NAMASTE and biomedical value sets"""
    
    resourceType: Literal["ValueSet"] = Field(default="ValueSet")
    
    # Required elements
    url: Optional[str] = Field(None, description="Canonical identifier for this value set")
    identifier: Optional[List[Identifier]] = Field(None, description="Additional identifiers")
    version: Optional[str] = Field(None, description="Business version of the value set")
    name: Optional[str] = Field(None, description="Name for this value set (computer friendly)")
    title: Optional[str] = Field(None, description="Name for this value set (human friendly)")
    status: PublicationStatusEnum = Field(..., description="Publication status")
    experimental: Optional[bool] = Field(None, description="For testing purposes, not real usage")
    date: Optional[datetime] = Field(None, description="Date last changed")
    publisher: Optional[str] = Field(None, description="Name of the publisher")
    contact: Optional[List[ContactDetail]] = Field(None, description="Contact details for the publisher")
    description: Optional[str] = Field(None, description="Natural language description")
    useContext: Optional[List[UsageContext]] = Field(None, description="Context the content is intended to support")
    jurisdiction: Optional[List[CodeableConcept]] = Field(None, description="Intended jurisdiction")
    
    # ValueSet specific elements
    immutable: Optional[bool] = Field(None, description="Indicates whether or not any change to the content logical definition may occur")
    purpose: Optional[str] = Field(None, description="Why this value set is defined")
    copyright: Optional[str] = Field(None, description="Use and/or publishing restrictions")
    
    # Compose and expansion
    compose: Optional[ValueSetCompose] = Field(None, description="Content logical definition of the value set")
    expansion: Optional[ValueSetExpansion] = Field(None, description="Used when the value set is 'expanded'")
    
    @field_validator('url')
    def validate_url(cls, v):
        if v and not validate_canonical(v):
            raise ValueError('Invalid canonical URL format')
        return v


class BundleLink(DomainResource):
    """Bundle link"""
    relation: str = Field(..., description="Relationship between this resource and the URI")
    url: str = Field(..., description="Reference details for the link")


class BundleEntry(DomainResource):
    """Bundle entry"""
    link: Optional[List[BundleLink]] = Field(None, description="Links related to this entry")
    fullUrl: Optional[str] = Field(None, description="URI for resource")
    resource: Optional[Union[CodeSystem, ConceptMap, ValueSet, Dict[str, Any]]] = Field(None, description="A resource in the bundle")
    search: Optional[Dict[str, Any]] = Field(None, description="Search related information")
    request: Optional[Dict[str, Any]] = Field(None, description="Additional execution information")
    response: Optional[Dict[str, Any]] = Field(None, description="Results of execution")


class Bundle(DomainResource):
    """FHIR R4 Bundle resource for collections of terminology resources"""
    
    resourceType: Literal["Bundle"] = Field(default="Bundle")
    
    # Required elements
    identifier: Optional[Identifier] = Field(None, description="Persistent identifier for the bundle")
    type: BundleTypeEnum = Field(..., description="Bundle type")
    timestamp: Optional[datetime] = Field(None, description="When the bundle was assembled")
    total: Optional[int] = Field(None, description="If search, the total number of matches")
    link: Optional[List[BundleLink]] = Field(None, description="Links related to this Bundle")
    entry: Optional[List[BundleEntry]] = Field(None, description="Entry in the bundle - will have a resource or information")
    signature: Optional[Dict[str, Any]] = Field(None, description="Digital Signature")
    
    @field_validator('total')
    def validate_total(cls, v, values):
        """Validate total is provided for searchset bundles"""
        bundle_type = values.get('type')
        if bundle_type == BundleTypeEnum.SEARCHSET and v is None:
            raise ValueError('Total must be provided for searchset bundles')
        return v


class CodeSystem(DomainResource):
    """FHIR R4 CodeSystem resource for NAMASTE and biomedical terminologies"""
    
    resourceType: Literal["CodeSystem"] = Field(default="CodeSystem")
    
    # Required elements
    url: Optional[str] = Field(None, description="Canonical identifier for this code system")
    identifier: Optional[List[Identifier]] = Field(None, description="Additional identifiers")
    version: Optional[str] = Field(None, description="Business version of the code system")
    name: Optional[str] = Field(None, description="Name for this code system (computer friendly)")
    title: Optional[str] = Field(None, description="Name for this code system (human friendly)")
    status: PublicationStatusEnum = Field(..., description="Publication status")
    experimental: Optional[bool] = Field(None, description="For testing purposes, not real usage")
    date: Optional[datetime] = Field(None, description="Date last changed")
    publisher: Optional[str] = Field(None, description="Name of the publisher")
    contact: Optional[List[ContactDetail]] = Field(None, description="Contact details for the publisher")
    description: Optional[str] = Field(None, description="Natural language description")
    useContext: Optional[List[UsageContext]] = Field(None, description="Context the content is intended to support")
    jurisdiction: Optional[List[CodeableConcept]] = Field(None, description="Intended jurisdiction")
    
    # CodeSystem specific elements
    purpose: Optional[str] = Field(None, description="Why this code system is defined")
    copyright: Optional[str] = Field(None, description="Use and/or publishing restrictions")
    caseSensitive: Optional[bool] = Field(None, description="If code comparison is case sensitive")
    valueSet: Optional[str] = Field(None, description="Canonical reference to the value set")
    hierarchyMeaning: Optional[str] = Field(None, pattern="^(grouped-by|is-a|part-of|classified-with)$")
    compositional: Optional[bool] = Field(None, description="If code system defines a compositional grammar")
    versionNeeded: Optional[bool] = Field(None, description="If definitions are not stable")
    content: str = Field(..., pattern="^(not-present|example|fragment|complete|supplement)$")
    supplements: Optional[str] = Field(None, description="Canonical URL of Code System this adds to")
    count: Optional[int] = Field(None, description="Total concepts in the code system")
    
    # Filters and properties
    filter: Optional[List[CodeSystemFilter]] = Field(None, description="Filter that can be used in a value set")
    property: Optional[List[CodeSystemProperty]] = Field(None, description="Additional information supplied about each concept")
    concept: Optional[List[CodeSystemConcept]] = Field(None, description="Concepts in the code system")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if v and not validate_canonical(v):
            raise ValueError('Invalid canonical URL format')
        return v
    
    @field_validator('valueSet')
    @classmethod
    def validate_valueset_url(cls, v):
        if v and not validate_canonical(v):
            raise ValueError('Invalid ValueSet canonical URL format')
        return v
    
    @field_validator('supplements')
    @classmethod
    def validate_supplements_url(cls, v):
        if v and not validate_canonical(v):
            raise ValueError('Invalid supplements canonical URL format')
        return v


# Update forward references
CodeSystemConcept.model_rebuild()
ConceptMapGroup.model_rebuild()
ConceptMapElement.model_rebuild()
ValueSetCompose.model_rebuild()
ValueSetExpansion.model_rebuild()
ValueSetExpansionContains.model_rebuild()
BundleEntry.model_rebuild()
ParametersParameterPart.model_rebuild()
ParametersParameter.model_rebuild()