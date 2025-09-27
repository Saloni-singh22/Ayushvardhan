# SIH 2025 Terminology Microservice Roadmap

## 🎯 Objectives
- Benchmark the current NAMASTE ↔ ICD-11/TM2 integration against Smart India Hackathon 2025 expectations.
- Spot technical, compliance, and operational gaps that could block FHIR R4 and India EHR 2016 readiness.
- Define a mapping and terminology management strategy that scales to dual coding (NAMASTE + ICD-11 TM2/Biomedicine).

## 🔍 Workstreams & Key Questions

### 1. Architecture & Compliance Review
- How closely do current FastAPI modules, middlewares, and database abstractions align with 2016 EHR standards (FHIR R4, ISO 22600, ABHA OAuth 2.0, audit trails)?
- Are security controls (OAuth scope, consent metadata, versioning) enforced end-to-end or merely stubbed?

### 2. Terminology Data Ingestion
- Confirm how NAMASTE CSV/Excel files are transformed into FHIR `CodeSystem` resources and persisted.
- Evaluate WHO ICD-11 API integration (token lifecycle, rate limits, caching, pagination).
- Check whether Biomedicine linearization is harmonised alongside TM2.

### 3. Mapping & Translation Logic
- Assess the deterministic and heuristic layers for NAMASTE ↔ TM2/Biomedicine matching.
- Validate ConceptMap creation, including equivalence semantics (`relatedto`, `inexact`, `narrower`, etc.).
- Identify failure handling for unmappable concepts and confidence scoring.

### 4. Developer & Clinical UX
- Review API surface for auto-complete, `$translate`, and bundle ingestion.
- Analyse audit dashboards and analytics endpoints for actionable insights.

## ✅ Deliverables for This Iteration
1. **Gap Analysis** – critique of current backend against SIH brief (functional + regulatory).
2. **Risk Register** – prioritized list of blockers/anti-patterns (data, auth, FHIR compliance, ops).
3. **Mapping Blueprint** – refined algorithm and data model for dual coding, with pseudocode/snippets.
4. **Next Steps** – scoped tasks for engineering, data stewardship, and validation.

## 📌 Success Criteria
- Clear traceability from each SIH requirement to implementation gaps/actions.
- Actionable mapping strategy accommodating direct, semantic, and biomedical bridges.
- Recommendations that can be implemented without rewriting the entire stack.

---
_This plan guides the critique and solutioning that follow in the session. Updates will be appended as new insights emerge._
