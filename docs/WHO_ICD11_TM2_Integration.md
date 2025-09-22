# WHO ICD-11 TM2 Integration

This document describes how to use the WHO ICD-11 Traditional Medicine (TM2) integration features in the FHIR terminology service.

## Overview

The WHO ICD-11 TM2 integration allows you to:
- Authenticate with WHO APIs using OAuth2 client credentials
- Search and retrieve WHO ICD-11 Traditional Medicine entities
- Convert WHO entities to FHIR R4 CodeSystem resources
- Store and serve FHIR-compliant WHO data in your terminology service

## Setup

### 1. Environment Configuration

Add your WHO API credentials to your `.env` file:

```bash
# WHO ICD-11 API Configuration
WHO_ICD_CLIENT_ID=your_client_id_here
WHO_ICD_CLIENT_SECRET=your_client_secret_here
WHO_ICD_TOKEN_URL=https://icdaccessmanagement.who.int/connect/token
WHO_ICD_BASE_URL=https://id.who.int/icd
WHO_ICD_API_VERSION=release/11/2023-01/mms

# Optional: Custom rate limiting
WHO_ICD_REQUESTS_PER_MINUTE=200
```

### 2. Obtain WHO API Credentials

1. Register at: https://icd.who.int/icdapi
2. Create an application and obtain client credentials
3. Note your `client_id` and `client_secret`
4. Ensure your application has access to ICD-11 MMS data

## API Endpoints

### Health Check

Check if WHO API is accessible:

```bash
GET /api/v1/who-icd/health
```

**Response:**
```json
{
    "status": "healthy",
    "message": "WHO ICD-11 API is accessible",
    "timestamp": "2024-01-15T10:30:00Z",
    "api_version": "release/11/2023-01/mms",
    "search_test": "successful"
}
```

### Search Entities

Search for WHO ICD-11 TM2 entities:

```bash
POST /api/v1/who-icd/search?term=acupuncture&limit=10&tm2_only=true
```

**Parameters:**
- `term`: Search term (empty for all entities)
- `limit`: Number of results (1-100, default 30)
- `offset`: Pagination offset (default 0)
- `tm2_only`: Filter for TM2 entities only (default true)
- `include_details`: Include detailed entity information (default false)

**Response:**
```json
{
    "success": true,
    "search_term": "acupuncture",
    "entities": [
        {
            "id": "334423054",
            "code": "XK7G",
            "title": "Acupuncture",
            "uri": "http://id.who.int/icd/entity/334423054",
            "is_tm2_related": true
        }
    ],
    "pagination": {
        "limit": 10,
        "offset": 0,
        "count": 1,
        "total_found": 1,
        "has_more": false
    }
}
```

### Get Entity Details

Get detailed information for a specific entity:

```bash
GET /api/v1/who-icd/entity/334423054
```

**Response:**
```json
{
    "success": true,
    "entity": {
        "id": "334423054",
        "code": "XK7G",
        "title": "Acupuncture",
        "definition": "A therapeutic intervention involving the insertion of needles...",
        "uri": "http://id.who.int/icd/entity/334423054",
        "parent": ["http://id.who.int/icd/entity/123456789"],
        "child": [],
        "is_tm2_related": true,
        "browserUrl": "https://icd.who.int/browse11/l-m/en#/http://id.who.int/icd/entity/334423054"
    }
}
```

### Sync TM2 Data

Retrieve WHO ICD-11 TM2 entities and convert to FHIR CodeSystems:

```bash
POST /api/v1/who-icd/sync/tm2?max_entities=1000&save_to_database=true&create_by_category=true
```

**Parameters:**
- `max_entities`: Maximum entities to retrieve (null for all)
- `batch_size`: Batch size for retrieval (10-100, default 50)
- `save_to_database`: Save CodeSystems to database (default true)
- `create_by_category`: Create separate CodeSystems by TM category (default true)

**Response:**
```json
{
    "success": true,
    "message": "WHO ICD-11 TM2 sync started in background",
    "parameters": {
        "max_entities": 1000,
        "batch_size": 50,
        "save_to_database": true,
        "create_by_category": true
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "note": "Check /who-icd/sync/status for progress updates"
}
```

### Search by Keywords

Search for TM2 entities using predefined keywords:

```bash
GET /api/v1/who-icd/search/keywords?keywords=acupuncture,herbal,massage&save_to_database=false
```

**Response:**
```json
{
    "success": true,
    "keywords_searched": ["acupuncture", "herbal", "massage"],
    "total_entities_found": 15,
    "entities_by_keyword": {
        "acupuncture": [
            {
                "id": "334423054",
                "code": "XK7G",
                "title": "Acupuncture",
                "uri": "http://id.who.int/icd/entity/334423054"
            }
        ],
        "herbal": [...],
        "massage": [...]
    },
    "saved_to_database": false
}
```

### List CodeSystems

List all FHIR CodeSystems created from WHO ICD-11 TM2 data:

```bash
GET /api/v1/who-icd/codesystems
```

**Response:**
```json
{
    "success": true,
    "codesystems": [
        {
            "_id": "who-icd11-tm2-acupuncture-2024",
            "id": "who-icd11-tm2-acupuncture-2024",
            "url": "http://who.int/icd11/tm2/acupuncture",
            "version": "2023-01",
            "name": "WHOICD11TM2Acupuncture",
            "title": "WHO ICD-11 TM2 - Acupuncture",
            "description": "WHO ICD-11 Traditional Medicine entities for Acupuncture",
            "count": 25,
            "tm2_category": "acupuncture",
            "sync_timestamp": "2024-01-15T10:30:00Z",
            "status": "active"
        }
    ],
    "total_count": 1
}
```

## Usage Examples

### 1. Basic WHO API Health Check

```python
import httpx

async def check_who_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/v1/who-icd/health")
        return response.json()
```

### 2. Search for Traditional Medicine Practices

```python
async def search_tm_practices():
    params = {
        "term": "traditional medicine",
        "limit": 50,
        "tm2_only": True,
        "include_details": True
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/who-icd/search",
            params=params
        )
        return response.json()
```

### 3. Sync All TM2 Data

```python
async def sync_all_tm2_data():
    params = {
        "max_entities": None,  # Get all entities
        "batch_size": 100,
        "save_to_database": True,
        "create_by_category": True
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/who-icd/sync/tm2",
            params=params
        )
        return response.json()
```

### 4. Search by Multiple Keywords

```python
async def search_by_keywords():
    keywords = "acupuncture,herbal medicine,ayurveda,traditional chinese medicine"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/who-icd/search/keywords?keywords={keywords}&save_to_database=true"
        )
        return response.json()
```

## Generated FHIR CodeSystems

When you sync WHO ICD-11 TM2 data, the system creates FHIR R4 CodeSystem resources with:

### CodeSystem Structure
```json
{
    "resourceType": "CodeSystem",
    "id": "who-icd11-tm2-acupuncture-2024",
    "url": "http://who.int/icd11/tm2/acupuncture",
    "version": "2023-01",
    "name": "WHOICD11TM2Acupuncture",
    "title": "WHO ICD-11 TM2 - Acupuncture",
    "status": "active",
    "experimental": false,
    "publisher": "World Health Organization",
    "description": "WHO ICD-11 Traditional Medicine entities for Acupuncture",
    "content": "complete",
    "count": 25,
    "concept": [
        {
            "code": "XK7G",
            "display": "Acupuncture",
            "definition": "A therapeutic intervention involving the insertion of needles...",
            "property": [
                {
                    "code": "parentId",
                    "valueString": "http://id.who.int/icd/entity/123456789"
                },
                {
                    "code": "browserUrl",
                    "valueString": "https://icd.who.int/browse11/l-m/en#/http://id.who.int/icd/entity/334423054"
                }
            ]
        }
    ]
}
```

### Properties Added to Concepts
- `parentId`: Parent entity URI
- `browserUrl`: WHO browser URL for the entity
- `blockId`: ICD-11 block identifier
- `classKind`: Entity classification type

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Entity not found
- `500`: Internal server error
- `503`: WHO API unavailable

Error responses include detailed error information:

```json
{
    "detail": {
        "status": "unhealthy",
        "message": "WHO ICD-11 API is not accessible: Authentication failed",
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

## Rate Limiting

The WHO API client includes built-in rate limiting:
- Default: 200 requests per minute
- Configurable via `WHO_ICD_REQUESTS_PER_MINUTE`
- Automatic retry with exponential backoff

## Database Storage

When `save_to_database=true`, the system stores:

1. **CodeSystems Collection**: Complete FHIR CodeSystem resources
2. **WHO ICD Codes Collection**: Individual entities for fast lookup

Each document includes:
- `source`: "WHO_ICD11_TM2"
- `tm2_category`: Traditional medicine category
- `sync_timestamp`: When the data was synced
- Full FHIR metadata

## Integration with Existing FHIR Endpoints

The WHO TM2 CodeSystems integrate seamlessly with existing FHIR endpoints:

```bash
# List all CodeSystems (including WHO TM2)
GET /api/v1/CodeSystem

# Get specific WHO TM2 CodeSystem
GET /api/v1/CodeSystem/who-icd11-tm2-acupuncture-2024

# Search concepts within WHO TM2 CodeSystem
GET /api/v1/CodeSystem/who-icd11-tm2-acupuncture-2024/$lookup?code=XK7G
```

## Monitoring and Logging

All WHO API operations are logged with appropriate levels:
- INFO: Successful operations, progress updates
- WARNING: Rate limiting, partial failures
- ERROR: Authentication failures, API errors

Check application logs for detailed operation status.