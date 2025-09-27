# Dual-Coding Mapping Blueprint

_Reference implementation notes for NAMASTE ↔ ICD-11 (TM2 & Biomedicine) mapping_

## 1. Pipeline Overview

1. **Ingestion**
   - Normalize NAMASTE CSVs into `CodeSystem` + `ConceptMap` seed tables (`namaste_codes`, `traditional_synonyms`).
   - Pull WHO ICD-11 content via scheduled background jobs; persist TM2 + MMS (biomedicine) variants with provenance fields (`release_id`, `linearization`, `last_sync`).

2. **Candidate Retrieval**
   - **Lexical**: Token-based search (Snowball stemmer, transliteration for Sanskrit/Tamil/Arabic) using MongoDB text index + WHO search API.
   - **Semantic**: Optional embedding lookup (e.g., `sentence-transformers` fine-tuned on medical corpora) stored in `knn_vectors` collection.
   - **Rule-based**: Jump tables for dosha/pattern/treatment families (Kapha → XK7G.2, Panchakarma → XK8Y.0, etc.).

3. **Scoring Matrix**
   | Signal | Description | Weight |
   |--------|-------------|--------|
   | Lexical overlap | Jaro–Winkler + token Jaccard | 0.35 |
   | Definition similarity | Cosine similarity on definition embeddings | 0.25 |
   | Synonym match | Direct match via NAMASTE designations | 0.20 |
   | Category alignment | Dosha/system vs ICD chapter metadata | 0.15 |
   | Clinical validation | Human-reviewed score (default 0) | 0.05 |

   Total score ≥ 0.75 → `equivalence="equivalent"`, 0.55–0.74 → `equivalence="relatedto"`, 0.35–0.54 → `equivalence="narrower"`, else fallback or reject.

4. **Mapping Decision Tree**
   1. If TM2 candidate ≥ 0.7 → **Tier 1** (Traditional).
   2. Else if MMS candidate ≥ 0.6 → **Tier 2** (Biomedicine; ensure `mapTarget` flagged as insurance-safe).
   3. Else if rule-based semantic mapping exists → **Tier 3**.
   4. Else → **Tier 4** (unmapped; emit `DataRequirement` for WHO feedback).

5. **Persistence & Versioning**
   - Store results in `code_mappings` collection with compound key `(source_system, source_code, target_system, release_id)`.
   - Maintain `MappingRun` documents capturing job metadata (`job_id`, `git_sha`, `namaste_release`, `who_release`, start/end timestamps, metrics).
   - Attach audit entries referencing `MappingRun.job_id` for traceability.

## 2. Reference Pydantic Models

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class MappingTier(str, Enum):
    DIRECT_TM2 = "direct_tm2"
    BIOMEDICAL = "biomedical"
    SEMANTIC = "semantic"
    UNMAPPABLE = "unmappable"

class MappingCandidate(BaseModel):
    source_code: str
    source_display: str
    target_code: str
    target_display: str
    target_system: str
    score: float
    tier: MappingTier
    equivalence: str
    evidence: dict

class MappingRecord(MappingCandidate):
    job_id: str
    namaste_release: str
    who_release: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewer_score: float | None = None
    reviewer_notes: str | None = None
```

## 3. Sample Mapping Engine Skeleton

```python
class MappingEngine:
    def __init__(self, namaste_repo, who_repo, embedding_service):
        self.namaste_repo = namaste_repo
        self.who_repo = who_repo
        self.embedding_service = embedding_service

    async def map_code(self, namaste_code: str) -> list[MappingCandidate]:
        term = await self.namaste_repo.get_term(namaste_code)
        if not term:
            return []

        lexical_candidates = await self.who_repo.search_lexical(term)
        embedding_candidates = await self.embedding_service.search(term)
        rule_candidates = self.namaste_repo.rule_based(term)

        merged = self._dedupe_candidates(
            lexical_candidates + embedding_candidates + rule_candidates
        )

        scored = [self._score_candidate(term, candidate) for candidate in merged]
        tiered = [self._assign_tier(candidate) for candidate in scored]

        return [c for c in tiered if c.score >= 0.35]

    def _score_candidate(self, term, candidate):
        # Combine weighted signals (lexical, semantic, category, validation)
        score_components = compute_signals(term, candidate)
        candidate.score = sum(weight * value for weight, value in score_components)
        candidate.evidence = {"signals": score_components}
        return candidate

    def _assign_tier(self, candidate):
        if candidate.target_system.endswith("tm2") and candidate.score >= 0.7:
            candidate.tier = MappingTier.DIRECT_TM2
            candidate.equivalence = "equivalent"
        elif candidate.target_system.endswith("mms") and candidate.score >= 0.6:
            candidate.tier = MappingTier.BIOMEDICAL
            candidate.equivalence = "relatedto"
        elif candidate.target_system.endswith("semantic"):
            candidate.tier = MappingTier.SEMANTIC
            candidate.equivalence = "narrower"
        else:
            candidate.tier = MappingTier.UNMAPPABLE
            candidate.equivalence = "unmatched"
        return candidate
```

## 4. FHIR ConceptMap Construction

```python
from app.models.fhir.resources import ConceptMap, ConceptMapGroup, ConceptMapGroupElement

def build_concept_map(job_id: str, mappings: list[MappingRecord]) -> ConceptMap:
    groups: dict[tuple[str, str], ConceptMapGroup] = {}

    for record in mappings:
        key = (record.source_system, record.target_system)
        group = groups.setdefault(key, ConceptMapGroup(source=key[0], target=key[1], element=[]))

        group.element.append(
            ConceptMapGroupElement(
                code=record.source_code,
                display=record.source_display,
                target=[{
                    "code": record.target_code,
                    "display": record.target_display,
                    "equivalence": record.equivalence,
                    "comment": f"score={record.score:.2f}; tier={record.tier}"
                }]
            )
        )

    concept_map = ConceptMap(
        id=f"namaste-who-{job_id}",
        status="active",
        sourceUri="http://namaste.ayush.gov.in/fhir/CodeSystem/namaste",
        targetUri="http://id.who.int/icd/release/11",
        group=list(groups.values())
    )
    return concept_map
```

## 5. Translation Operation (`$translate`) Enhancement

- Cache lookup results per `(source_system, source_code, target_system)` with TTL to avoid repeated DB hits.
- Return full FHIR `Parameters` resource:

```json
{
  "resourceType": "Parameters",
  "parameter": [
    {"name": "result", "valueBoolean": true},
    {"name": "match", "part": [
      {"name": "equivalence", "valueCode": "relatedto"},
      {"name": "concept", "valueCoding": {
        "system": "http://id.who.int/icd/release/11/mms",
        "code": "5A11",
        "display": "Type 2 diabetes mellitus"
      }},
      {"name": "product", "valueCoding": {
        "system": "http://id.who.int/icd/release/11/mms/tm2",
        "code": "XM1TD2",
        "display": "Madhumeha (Prameha subtype)"
      }},
      {"name": "comment", "valueString": "score=0.82; reviewer=dr_raman"}
    ]}
  ]
}
```

## 6. Clinical Validation Loop

1. Expose `/mapping/validation` endpoint to accept clinician feedback (score, notes, reviewer ID).
2. Persist validations in `mapping_validations` collection; update `MappingRecord.reviewer_score` via weighted moving average.
3. Surface validation backlog in dashboard and require sign-off for Tier 2 mappings before production usage.

## 7. Monitoring & Metrics

Track the following KPIs per mapping run:
- `%` of NAMASTE codes mapped by tier.
- Average confidence score per medical system (Ayurveda, Siddha, Unani).
- WHO API QPS, error rate, and token refresh count.
- Clinical validation coverage vs outstanding items.

Emit metrics via Prometheus `/metrics` (e.g., `mapping_confidence_bucket`, `who_api_http_duration_seconds`).

---
_Use this blueprint to refactor `NAMASTEWHOMappingService` and the enhanced mapping module into a maintainable, compliant dual-coding engine._
