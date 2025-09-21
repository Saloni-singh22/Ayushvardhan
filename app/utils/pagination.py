"""
Pagination utilities for FHIR API responses
"""

from typing import Dict, Any, List, Optional
from math import ceil
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters for FHIR searches"""
    count: int = Field(default=50, ge=1, le=1000, description="Number of results per page")
    offset: int = Field(default=0, ge=0, description="Starting offset")
    sort: Optional[str] = Field(default=None, description="Sort field")
    sort_order: str = Field(default="asc", regex="^(asc|desc)$", description="Sort order")


class PaginationResult(BaseModel):
    """Pagination result metadata"""
    total: int
    count: int
    offset: int
    has_next: bool
    has_prev: bool
    total_pages: int
    current_page: int


def paginate_results(
    results: List[Dict[str, Any]],
    total: int,
    count: int,
    offset: int,
    base_url: str,
    query_params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Paginate FHIR search results and create navigation links
    
    Args:
        results: List of resource dictionaries
        total: Total number of matching resources
        count: Requested page size
        offset: Starting offset
        base_url: Base URL for navigation links
        query_params: Additional query parameters
    
    Returns:
        Dictionary with pagination metadata and navigation links
    """
    if query_params is None:
        query_params = {}
    
    # Calculate pagination metadata
    current_page = (offset // count) + 1
    total_pages = ceil(total / count) if count > 0 else 1
    has_next = offset + count < total
    has_prev = offset > 0
    
    # Create navigation links
    links = []
    
    # Self link
    self_params = {**query_params, "_count": count, "_offset": offset}
    self_query = "&".join([f"{k}={v}" for k, v in self_params.items() if v is not None])
    links.append({
        "relation": "self",
        "url": f"{base_url}?{self_query}" if self_query else base_url
    })
    
    # First link
    if has_prev:
        first_params = {**query_params, "_count": count, "_offset": 0}
        first_query = "&".join([f"{k}={v}" for k, v in first_params.items() if v is not None])
        links.append({
            "relation": "first",
            "url": f"{base_url}?{first_query}" if first_query else base_url
        })
    
    # Previous link
    if has_prev:
        prev_offset = max(0, offset - count)
        prev_params = {**query_params, "_count": count, "_offset": prev_offset}
        prev_query = "&".join([f"{k}={v}" for k, v in prev_params.items() if v is not None])
        links.append({
            "relation": "prev", 
            "url": f"{base_url}?{prev_query}" if prev_query else base_url
        })
    
    # Next link
    if has_next:
        next_offset = offset + count
        next_params = {**query_params, "_count": count, "_offset": next_offset}
        next_query = "&".join([f"{k}={v}" for k, v in next_params.items() if v is not None])
        links.append({
            "relation": "next",
            "url": f"{base_url}?{next_query}" if next_query else base_url
        })
    
    # Last link
    if has_next:
        last_offset = ((total_pages - 1) * count) if total_pages > 0 else 0
        last_params = {**query_params, "_count": count, "_offset": last_offset}
        last_query = "&".join([f"{k}={v}" for k, v in last_params.items() if v is not None])
        links.append({
            "relation": "last",
            "url": f"{base_url}?{last_query}" if last_query else base_url
        })
    
    pagination_result = PaginationResult(
        total=total,
        count=len(results),
        offset=offset,
        has_next=has_next,
        has_prev=has_prev,
        total_pages=total_pages,
        current_page=current_page
    )
    
    return {
        "pagination": pagination_result,
        "links": links
    }


def apply_sorting(cursor, sort_field: Optional[str], sort_order: str = "asc"):
    """
    Apply sorting to MongoDB cursor
    
    Args:
        cursor: MongoDB cursor
        sort_field: Field to sort by
        sort_order: Sort order (asc/desc)
    
    Returns:
        Sorted cursor
    """
    if sort_field:
        direction = 1 if sort_order.lower() == "asc" else -1
        
        # Handle special FHIR sort fields
        if sort_field == "_lastUpdated":
            sort_field = "meta.lastUpdated"
        elif sort_field == "_id":
            sort_field = "_id"
        
        cursor = cursor.sort(sort_field, direction)
    
    return cursor


def build_search_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build MongoDB query from FHIR search parameters
    
    Args:
        params: FHIR search parameters
    
    Returns:
        MongoDB query dictionary
    """
    query = {}
    
    for key, value in params.items():
        if value is None or key.startswith("_"):
            continue
        
        # Handle different parameter types
        if key in ["url", "name", "title"]:
            if key == "url":
                query["url"] = value
            else:
                # Case-insensitive search for text fields
                query[key] = {"$regex": value, "$options": "i"}
        
        elif key in ["status", "content"]:
            query[key] = value
        
        elif key == "publisher":
            query["publisher"] = {"$regex": value, "$options": "i"}
        
        elif key == "jurisdiction":
            query["jurisdiction.coding.code"] = value
        
        # NAMASTE specific parameters
        elif key == "ayush_system":
            query["ayush_system"] = value
        
        elif key == "dosha":
            query["namaste_concepts.ayurveda_properties.doshagnata"] = value
        
        # WHO ICD-11 specific parameters
        elif key == "icd11_module":
            query["icd11_module"] = value
        
        elif key == "traditional_system":
            query["tm2_concepts.traditional_system"] = value
        
        # ConceptMap specific parameters
        elif key == "source":
            query["source"] = value
        
        elif key == "target":
            query["target"] = value
        
        elif key == "source-code":
            query["group.element.code"] = value
        
        elif key == "target-code":
            query["group.element.target.code"] = value
        
        # ValueSet specific parameters
        elif key == "code":
            query["$or"] = [
                {"compose.include.concept.code": value},
                {"expansion.contains.code": value}
            ]
    
    return query


def extract_text_search(params: Dict[str, Any]) -> Optional[str]:
    """
    Extract text search parameter from FHIR search parameters
    
    Args:
        params: FHIR search parameters
    
    Returns:
        Text search string or None
    """
    return params.get("_text") or params.get("_content")


def validate_pagination_params(count: int, offset: int) -> List[str]:
    """
    Validate pagination parameters
    
    Args:
        count: Page size
        offset: Starting offset
    
    Returns:
        List of validation errors
    """
    errors = []
    
    if count < 1:
        errors.append("_count must be at least 1")
    elif count > 1000:
        errors.append("_count cannot exceed 1000")
    
    if offset < 0:
        errors.append("_offset must be non-negative")
    
    return errors


def calculate_total_pages(total: int, count: int) -> int:
    """Calculate total number of pages"""
    return ceil(total / count) if count > 0 else 1


def get_page_number(offset: int, count: int) -> int:
    """Calculate current page number from offset and count"""
    return (offset // count) + 1 if count > 0 else 1


def create_pagination_summary(
    total: int,
    count: int, 
    offset: int,
    actual_count: int
) -> str:
    """
    Create human-readable pagination summary
    
    Returns:
        Summary string like "Showing 1-10 of 100 results"
    """
    if total == 0:
        return "No results found"
    
    start = offset + 1
    end = min(offset + actual_count, total)
    
    return f"Showing {start}-{end} of {total} results"