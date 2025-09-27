# Backend Gap Analysis – NAMASTE ↔ ICD-11 Terminology Service

_Last updated: 2025-09-26_

## 1. Regulatory & Security Compliance
- **Authentication bypass**: `AuthMiddleware` whitelists nearly every `/api/v1/*` route and allows anonymous access in debug mode, undermining ABHA OAuth 2.0 and ISO 22600 access-control requirements.
- **Missing ABDM handshake**: No integration with ABDM Gateway for token issuance, consent artefacts, or HIP/HIU session management; JWT validation only checks a 14-digit string.
- **Hard-coded secrets**: WHO API client credentials ship in source; environment validation absent (e.g., `jwt_secret_key` default fails length validator in `.env.example`).
- **Undefined configuration**: `settings.soft_delete` referenced in `codesystem.delete_code_system` but not defined, leading to runtime exceptions.
- **Audit incompleteness**: Audit middleware logs to MongoDB but lacks retention policies, consent linkage, or failure handling when DB unavailable.

## 2. FHIR & Terminology Service Gaps
- **Capability misalignment**: CapabilityStatement declares `$lookup`, `$validate-code`, `$expand`, `$translate`, but corresponding endpoints either return placeholders or lack full FHIR `Parameters` responses.
- **FHIR typing issues**: `namaste_who_mapping_service._create_namaste_who_conceptmap()` returns a Python `dict`, yet callers treat it like a Pydantic model (`concept_map.id`) causing `AttributeError` at runtime.
- **Partial resource coverage**: ValueSet and Bundle ingestion endpoints exist but do not enforce FHIR profiles or cardinality checks; no versioning or history endpoints for CodeSystems.
- **ConceptMap semantics**: Equivalence values limited to `wider`/`inexact`; no support for `narrower`, `relatedto`, or `not-related` which are critical for dual coding clarity.
- **Terminology caching**: WHO API responses aren’t cached; rate-limiting/back-off is minimal and could breach WHO API usage policy.

## 3. Mapping Logic & Data Quality
- **Single-pass heuristic**: Text overlap scoring is brittle; no normalization (stemming, diacritics), no SNOMED/LOINC bridging, no ontological hierarchy traversal.
- **No bi-directional persistence**: Mapping metadata stored once (`mapping_metadata` with `_id` hard-coded) prevents multi-version tracking and audit.
- **Enhanced mapping placeholders**: `/enhanced-mapping/status` and analytics endpoints return static JSON instead of computed statistics; clinical validation workflow is not persisted.
- **Concept duplication risk**: `_create_enhanced_who_codesystem` aggregates WHO entities but doesn’t deduplicate by linearization/stem, inflating CodeSystem counts.

## 4. Operational Readiness
- **Database dependency**: Application fails if MongoDB unavailable; no bootstrap fallback or graceful degradation for read-only operations.
- **Deployment mismatch**: `docker-compose.yml` lacks Mongo/Redis services referenced in code; `.env` defaults point to localhost without container networking.
- **Testing coverage**: No automated tests for mapping, WHO client retries, or FHIR validation; `tests/` directories are empty.
- **Logging & observability**: No structured metrics for WHO API latency, ABHA login success, or mapping success rate despite CapabilityStatement advertising `/metrics`.

## 5. Data Pipeline Concerns
- **CSV ingestion**: `csv_processor` parses files but doesn’t persist resulting `CodeSystem` into MongoDB or expose ingestion status endpoints.
- **WHO update sync**: Background task fetches TM2 entities but lacks resumable checkpoints or delta updates; no provenance of releases (Foundation vs MMS).
- **FHIR Bundle ingest**: Required encounter upload endpoint for dual-coded ProblemList resources is missing.

---
_This document feeds the critique and remediation strategy accompanying the Smart India Hackathon 2025 submission._
