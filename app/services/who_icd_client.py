"""
WHO ICD-11 TM2 API Client
Client for retrieving ICD-11 TM2 entities from WHO API endpoints
"""

import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
import logging
from datetime import datetime

from app.core.config import settings
from app.services.who_api_auth import who_auth_service

logger = logging.getLogger(__name__)


class WHOICD11TM2Entity:
    """Represents an ICD-11 TM2 entity from WHO API"""
    
    def __init__(self, data: Dict[str, Any]):
        # Handle both foundation and MMS linearization data formats
        self.id = data.get("@id", "") or data.get("id", "")
        self.title = data.get("title", {})
        self.definition = data.get("definition", {})
        self.uri = data.get("@id", "") or data.get("id", "")
        self.parent = data.get("parent", [])
        self.child = data.get("child", [])
        
        # MMS-specific fields
        self.theCode = data.get("theCode", "")
        self.stemId = data.get("stemId", "")
        self.chapter = data.get("chapter", "")
        
        # Foundation-specific fields
        self.inclusion = data.get("inclusion", {})
        self.exclusion = data.get("exclusion", {})
        self.postcoordinationAvailability = data.get("postcoordinationAvailability", {})
        self.codingNote = data.get("codingNote", {})
        self.blockId = data.get("blockId", "")
        self.codeRange = data.get("codeRange", {})
        self.classKind = data.get("classKind", "")
        self.browserUrl = data.get("browserUrl", "")
        
        # Raw data for additional processing
        self.raw_data = data
    
    @property
    def code(self) -> str:
        """Get ICD-11 code"""
        return self.theCode or self.codeRange.get("start", "") if isinstance(self.codeRange, dict) else ""
    
    @property
    def display_title(self) -> str:
        """Get display title in English"""
        if isinstance(self.title, dict):
            return self.title.get("@value", "") or self.title.get("en", "")
        return str(self.title) if self.title else ""
    
    @property
    def display_definition(self) -> str:
        """Get definition in English"""
        if isinstance(self.definition, dict):
            return self.definition.get("@value", "") or self.definition.get("en", "")
        return str(self.definition) if self.definition else ""
    
    @property
    def entity_id(self) -> str:
        """Extract entity ID from URI"""
        if self.uri:
            return self.uri.split("/")[-1]
        return self.id.split("/")[-1] if self.id else ""
    
    def is_tm2_related(self) -> bool:
        """Check if entity is related to Traditional Medicine chapters."""

        chapter_raw = str(self.raw_data.get("chapter", "")).strip().upper()
        if chapter_raw in {"26", "27", "TM1", "TM1 TM2", "TM2"}:
            return True

        title_lower = self.display_title.lower()
        definition_lower = self.display_definition.lower()

        tm_keywords = [
            "traditional medicine",
            "ayurveda",
            "unani",
            "siddha",
            "homeopathy",
            "naturopathy",
            "yoga",
            "acupuncture",
            "traditional chinese medicine",
            "tcm",
            "complementary medicine",
            "alternative medicine",
            "integrative medicine",
            "traditional healing",
            "herbal medicine",
            "traditional therapy",
        ]

        return any(
            keyword in title_lower or keyword in definition_lower for keyword in tm_keywords
        )


class WHOICD11TM2Client:
    """
    Client for WHO ICD-11 TM2 API operations
    Handles search, retrieval, and pagination of ICD-11 entities
    """
    
    def __init__(self):
        self.base_url = settings.who_icd_api_base_url
        self.api_version = settings.who_icd_api_version
        self.auth_service = who_auth_service
        
        # API endpoints - Updated for correct WHO API structure
        self.search_endpoint = f"{self.base_url}/{self.api_version}/search"
        self.entity_endpoint = f"{self.base_url}/{self.api_version}"
        
        # Rate limiting
        self._request_semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        self._last_request_time = 0
        self._min_request_interval = 0.2  # 200ms between requests
        self.max_retries = 3
        self.retry_backoff_factor = 0.5
    
    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make a rate-limited HTTP request"""
        async with self._request_semaphore:
            last_error: Optional[httpx.HTTPError] = None
            for attempt in range(1, self.max_retries + 1):
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - self._last_request_time
                if time_since_last < self._min_request_interval:
                    await asyncio.sleep(self._min_request_interval - time_since_last)

                headers = await self.auth_service.get_authenticated_headers()
                headers.update(kwargs.pop("headers", {}))

                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.request(method, url, headers=headers, **kwargs)
                    self._last_request_time = asyncio.get_event_loop().time()
                    response.raise_for_status()
                    return response
                except httpx.HTTPError as exc:
                    last_error = exc
                    logger.warning(
                        "WHO ICD request failed (attempt %d/%d): %s",
                        attempt,
                        self.max_retries,
                        exc,
                    )
                    if attempt >= self.max_retries:
                        raise
                    backoff = self.retry_backoff_factor * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff)

            if last_error:
                raise last_error
    
    async def search_entities(
        self, 
        term: str = "", 
        flat_results: bool = True,
        limit: int = 30,
        offset: int = 0,
        include_tm2_only: bool = True,
        chapter_filter: Optional[str] = None,
        use_flexi_search: bool = True,
    ) -> Dict[str, Any]:
        """
        Search ICD-11 entities
        
        Args:
            term: Search term (empty for all entities)
            flat_results: Whether to return flat results
            limit: Number of results per page
            offset: Offset for pagination
            include_tm2_only: Filter for TM-related entities only after retrieval
            chapter_filter: Optional WHO chapter filter (e.g. "TM1", "TM2", "TM1,TM2")
            use_flexi_search: Whether to enable WHO flexi search for fuzzy matches
            
        Returns:
            dict: Search response from WHO API
        """
        logger.info(f"Searching WHO ICD-11 entities: term='{term}', limit={limit}, offset={offset}")
        
        # WHO API requires non-empty search term
        if not term or term.strip() == "":
            term = "disease"  # Default search term if empty
        
        if include_tm2_only and not chapter_filter:
            chapter_filter = "TM1,TM2"

        # Use simplified query parameters for WHO API MMS endpoint
        search_params = {
            "q": term.strip()
        }
        
        # Add other parameters
        if flat_results:
            search_params["flatResults"] = "true"
        
        # Add pagination params if specified
        if limit:
            search_params["limit"] = str(limit)
        if offset:
            search_params["offset"] = str(offset)

        if chapter_filter:
            search_params["chapterFilter"] = chapter_filter

        if use_flexi_search:
            search_params["useFlexisearch"] = "true"
        
        try:
            response = await self._rate_limited_request(
                "GET",
                self.search_endpoint,
                params=search_params
            )
            
            search_results = response.json()
            
            # Filter for TM2-related entities if requested
            if include_tm2_only and "destinationEntities" in search_results:
                original_count = len(search_results["destinationEntities"])
                filtered_entities = []
                
                for entity_data in search_results["destinationEntities"]:
                    entity = WHOICD11TM2Entity(entity_data)
                    if entity.is_tm2_related():
                        filtered_entities.append(entity_data)
                
                search_results["destinationEntities"] = filtered_entities
                search_results["filteredCount"] = len(filtered_entities)
                search_results["originalCount"] = original_count
                
                logger.info(f"Filtered {original_count} entities to {len(filtered_entities)} TM2-related entities")
            
            return search_results
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to search WHO ICD-11 entities: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during WHO ICD-11 search: {e}")
            raise
    
    async def get_entity_details(self, entity_id: str) -> WHOICD11TM2Entity:
        """
        Get detailed information for a specific entity
        
        Args:
            entity_id: Entity ID or URI
            
        Returns:
            WHOICD11TM2Entity: Detailed entity information
        """
        # Clean entity ID from URI if needed
        if "/" in entity_id:
            entity_id = entity_id.split("/")[-1]
        
        entity_url = f"{self.entity_endpoint}/{entity_id}"
        
        logger.debug(f"Fetching WHO ICD-11 entity details: {entity_id}")
        
        try:
            response = await self._rate_limited_request("GET", entity_url)
            entity_data = response.json()
            
            return WHOICD11TM2Entity(entity_data)
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get WHO ICD-11 entity {entity_id}: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting WHO ICD-11 entity {entity_id}: {e}")
            raise
    
    async def get_all_tm2_entities(
        self, 
        max_entities: Optional[int] = None,
        batch_size: int = 30
    ) -> AsyncGenerator[WHOICD11TM2Entity, None]:
        """
        Get all TM2-related entities with pagination
        
        Args:
            max_entities: Maximum number of entities to retrieve (None for all)
            batch_size: Number of entities per batch
            
        Yields:
            WHOICD11TM2Entity: TM2-related entities
        """
        offset = 0
        total_retrieved = 0
        
        logger.info(f"Starting bulk retrieval of WHO ICD-11 TM2 entities")
        
        while True:
            # Check if we've reached the limit
            if max_entities and total_retrieved >= max_entities:
                break
            
            # Adjust batch size for last batch
            current_limit = batch_size
            if max_entities:
                remaining = max_entities - total_retrieved
                current_limit = min(batch_size, remaining)
            
            try:
                # Search for entities using Traditional Medicine keywords
                # Based on testing, use specific terms that return TM-related entities
                tm_search_terms = [
                    "acupuncture", "cupping", "moxibustion", "traditional",
                    "complementary", "herbal", "massage", "meditation",
                    "homeopathy", "naturopathy", "chiropractic", "osteopathy"
                ]
                
                current_term = tm_search_terms[offset // current_limit % len(tm_search_terms)]
                
                search_results = await self.search_entities(
                    term=current_term,
                    limit=current_limit,
                    offset=offset % current_limit,  # Reset offset for each term
                    include_tm2_only=True
                )
                
                entities = search_results.get("destinationEntities", [])
                
                if not entities:
                    logger.info("No more entities found, stopping pagination")
                    break
                
                # Yield each entity
                for entity_data in entities:
                    entity = WHOICD11TM2Entity(entity_data)
                    yield entity
                    total_retrieved += 1
                
                logger.info(f"Retrieved batch: {len(entities)} entities (total: {total_retrieved})")
                
                # Check if we've received fewer entities than requested (end of data)
                if len(entities) < current_limit:
                    logger.info("Received partial batch, reached end of data")
                    break
                
                offset += len(entities)
                
                # Small delay between batches to be respectful to the API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error during batch retrieval at offset {offset}: {e}")
                break
        
        logger.info(f"Completed TM2 entity retrieval: {total_retrieved} entities total")
    
    async def search_tm2_by_keywords(self, keywords: List[str]) -> List[WHOICD11TM2Entity]:
        """
        Search for TM2 entities using specific keywords
        
        Args:
            keywords: List of search keywords
            
        Returns:
            List[WHOICD11TM2Entity]: Found TM2 entities
        """
        all_entities = []
        
        for keyword in keywords:
            logger.info(f"Searching for TM2 entities with keyword: {keyword}")
            
            try:
                search_results = await self.search_entities(
                    term=keyword,
                    limit=50,
                    include_tm2_only=True
                )
                
                entities_data = search_results.get("destinationEntities", [])
                entities = [WHOICD11TM2Entity(data) for data in entities_data]
                
                # Avoid duplicates
                existing_ids = {entity.entity_id for entity in all_entities}
                new_entities = [e for e in entities if e.entity_id not in existing_ids]
                
                all_entities.extend(new_entities)
                logger.info(f"Found {len(new_entities)} new entities for keyword '{keyword}'")
                
                # Small delay between keyword searches
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error(f"Error searching for keyword '{keyword}': {e}")
                continue
        
        logger.info(f"Total unique TM2 entities found: {len(all_entities)}")
        return all_entities


# Global instance
who_icd_client = WHOICD11TM2Client()