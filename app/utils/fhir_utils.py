"""
FHIR utilities for creating standard FHIR resources and responses
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


def create_operation_outcome(
    severity: str = "error",
    code: str = "processing",
    details: str = "",
    diagnostics: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a FHIR OperationOutcome resource
    
    Args:
        severity: error, warning, information
        code: FHIR issue type code
        details: Human readable description
        diagnostics: Additional diagnostic information
    """
    operation_outcome = {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": severity,
                "code": code,
                "details": {
                    "text": details
                }
            }
        ]
    }
    
    if diagnostics:
        operation_outcome["issue"][0]["diagnostics"] = diagnostics
    
    return operation_outcome


def create_bundle_response(
    bundle_type: str = "searchset",
    total: int = 0,
    entries: List[Dict[str, Any]] = None,
    links: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a FHIR Bundle response
    
    Args:
        bundle_type: Bundle type (searchset, collection, etc.)
        total: Total number of matching resources
        entries: List of bundle entries
        links: Navigation links
    """
    bundle = {
        "resourceType": "Bundle",
        "type": bundle_type,
        "timestamp": datetime.utcnow().isoformat(),
        "total": total
    }
    
    if entries:
        bundle["entry"] = entries
    
    if links:
        bundle["link"] = links
    
    return bundle


def create_capability_statement() -> Dict[str, Any]:
    """
    Create FHIR CapabilityStatement for the terminology service
    """
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": datetime.utcnow().isoformat(),
        "publisher": "NAMASTE FHIR Terminology Service",
        "kind": "instance",
        "software": {
            "name": "NAMASTE Terminology Service",
            "version": "1.0.0"
        },
        "implementation": {
            "description": "FHIR R4 Terminology Service for India's NAMASTE and WHO ICD-11 integration"
        },
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [
            {
                "mode": "server",
                "resource": [
                    {
                        "type": "CodeSystem",
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"},
                            {"code": "create"},
                            {"code": "update"},
                            {"code": "delete"}
                        ],
                        "operation": [
                            {
                                "name": "validate-code",
                                "definition": "http://hl7.org/fhir/OperationDefinition/CodeSystem-validate-code"
                            },
                            {
                                "name": "lookup",
                                "definition": "http://hl7.org/fhir/OperationDefinition/CodeSystem-lookup"
                            }
                        ]
                    },
                    {
                        "type": "ConceptMap",
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"},
                            {"code": "create"},
                            {"code": "update"},
                            {"code": "delete"}
                        ],
                        "operation": [
                            {
                                "name": "translate",
                                "definition": "http://hl7.org/fhir/OperationDefinition/ConceptMap-translate"
                            }
                        ]
                    },
                    {
                        "type": "ValueSet",
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"},
                            {"code": "create"},
                            {"code": "update"},
                            {"code": "delete"}
                        ],
                        "operation": [
                            {
                                "name": "expand",
                                "definition": "http://hl7.org/fhir/OperationDefinition/ValueSet-expand"
                            },
                            {
                                "name": "validate-code",
                                "definition": "http://hl7.org/fhir/OperationDefinition/ValueSet-validate-code"
                            }
                        ]
                    }
                ]
            }
        ]
    }


def validate_fhir_resource(resource: Dict[str, Any], resource_type: str) -> List[str]:
    """
    Validate basic FHIR resource structure
    
    Returns:
        List of validation errors
    """
    errors = []
    
    if not resource.get("resourceType"):
        errors.append("Missing required field: resourceType")
    elif resource["resourceType"] != resource_type:
        errors.append(f"Invalid resourceType: expected {resource_type}, got {resource.get('resourceType')}")
    
    # Basic FHIR validation rules
    if resource_type in ["CodeSystem", "ConceptMap", "ValueSet"]:
        if not resource.get("status"):
            errors.append("Missing required field: status")
        
        status_values = ["draft", "active", "retired", "unknown"]
        if resource.get("status") not in status_values:
            errors.append(f"Invalid status value: must be one of {status_values}")
    
    return errors


def create_search_parameters() -> Dict[str, Dict[str, Any]]:
    """
    Define FHIR search parameters for terminology resources
    """
    return {
        "CodeSystem": {
            "url": {
                "type": "uri",
                "description": "The canonical URL of the code system"
            },
            "name": {
                "type": "string", 
                "description": "Computer-friendly name of the code system"
            },
            "title": {
                "type": "string",
                "description": "Human-friendly title of the code system"
            },
            "status": {
                "type": "token",
                "description": "Publication status"
            },
            "publisher": {
                "type": "string",
                "description": "Publisher name"
            },
            "content": {
                "type": "token",
                "description": "Content type of the code system"
            },
            "_text": {
                "type": "string",
                "description": "Full-text search"
            }
        },
        "ConceptMap": {
            "url": {
                "type": "uri",
                "description": "The canonical URL of the concept map"
            },
            "source": {
                "type": "reference",
                "description": "Source value set"
            },
            "target": {
                "type": "reference", 
                "description": "Target value set"
            },
            "source-code": {
                "type": "token",
                "description": "Source concept code"
            },
            "target-code": {
                "type": "token",
                "description": "Target concept code"
            }
        },
        "ValueSet": {
            "url": {
                "type": "uri",
                "description": "The canonical URL of the value set"
            },
            "expansion": {
                "type": "uri",
                "description": "Value set expansion identifier"
            },
            "code": {
                "type": "token",
                "description": "Code contained in the value set"
            }
        }
    }


def format_fhir_datetime(dt: datetime) -> str:
    """Format datetime for FHIR compliance"""
    return dt.isoformat() + "Z"


def parse_fhir_datetime(dt_str: str) -> datetime:
    """Parse FHIR datetime string"""
    # Remove timezone info for simple parsing
    if dt_str.endswith('Z'):
        dt_str = dt_str[:-1]
    return datetime.fromisoformat(dt_str)


def create_coding(system: str, code: str, display: Optional[str] = None) -> Dict[str, Any]:
    """Create a FHIR Coding data type"""
    coding = {
        "system": system,
        "code": code
    }
    
    if display:
        coding["display"] = display
    
    return coding


def create_codeable_concept(
    system: str, 
    code: str, 
    display: Optional[str] = None,
    text: Optional[str] = None
) -> Dict[str, Any]:
    """Create a FHIR CodeableConcept data type"""
    concept = {
        "coding": [create_coding(system, code, display)]
    }
    
    if text:
        concept["text"] = text
    
    return concept


def extract_canonical_url(url: str) -> tuple[str, Optional[str]]:
    """
    Extract base URL and version from a canonical URL
    
    Returns:
        Tuple of (base_url, version)
    """
    if "|" in url:
        base_url, version = url.split("|", 1)
        return base_url, version
    return url, None


def build_canonical_url(base_url: str, version: Optional[str] = None) -> str:
    """Build canonical URL with optional version"""
    if version:
        return f"{base_url}|{version}"
    return base_url