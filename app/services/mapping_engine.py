"""Mapping engine for NAMASTE ↔ ICD-11 dual coding.

This module centralises the candidate generation, scoring, tiering and
persistence logic required to translate NAMASTE traditional medicine concepts
into ICD-11 (TM2 + MMS) counterparts.  The implementation follows the
architecture captured in ``docs/mapping_strategy_blueprint.md``.
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
import unicodedata
from collections import defaultdict
from enum import StrEnum
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

from bson import ObjectId
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.models.fhir.base import ConceptMapEquivalenceEnum
from app.models.fhir.resources import (
    ConceptMap,
    ConceptMapElement,
    ConceptMapGroup,
    ConceptMapTarget,
)
from app.services.who_icd_client import WHOICD11TM2Entity, who_icd_client

logger = logging.getLogger(__name__)

TM2_SYSTEM_URI = "http://id.who.int/icd/release/11/mms/tm2"
MMS_SYSTEM_URI = "http://id.who.int/icd/release/11/mms"
SEMANTIC_SYSTEM_URI = "http://namaste.ayush.gov.in/fhir/CodeSystem/semantic-bridge"
NAMASTE_SYSTEM_URI = "http://namaste.ayush.gov.in/fhir/CodeSystem/namaste"

TRADITIONAL_TO_CLINICAL_SYNONYMS: Dict[str, List[str]] = {
    "jwara": ["fever", "pyrexia", "febrile"],
    "vyadhi": ["disease", "disorder", "ailment"],
    "viniscaya": ["diagnosis", "assessment"],
    "shotha": ["edema", "swelling", "inflammation"],
    "atisara": ["diarrhea", "loose stools", "gastroenteritis"],
    "prameha": ["diabetes", "metabolic disorder", "hyperglycemia"],
    "kushtha": ["skin disease", "dermatitis", "psoriasis"],
    "kasa": ["cough", "bronchitis", "respiratory disorder"],
    "shwasa": ["asthma", "dyspnea", "breathing difficulty"],
    "unmada": ["mental disorder", "psychosis", "psychiatric"],
    "apasmara": ["epilepsy", "seizure", "convulsion"],
    "arsha": ["hemorrhoids", "piles"],
    "mutrakrichra": ["dysuria", "urinary disorder"],
    "raktapitta": ["bleeding disorder", "hemorrhage"],
    "dosha": ["constitutional pattern", "traditional medicine pattern", "body constitution"],
    "tridosha": ["three dosha theory", "constitutional imbalance"],
    "vata": [
        "wind dosha",
        "movement disorder",
        "traditional medicine vata",
        "wind",
        "wind pattern",
        "wind disorder",
        "liver wind pattern",
        "wind stroke",
    ],
    "pitta": [
        "fire dosha",
        "metabolic dosha",
        "heat",
        "fire",
        "heat pattern",
        "fire pattern",
        "liver heat pattern",
        "heat toxin",
    ],
    "kapha": [
        "water dosha",
        "structural dosha",
        "dampness",
        "phlegm",
        "dampness pattern",
        "phlegm pattern",
        "cold damp disorder",
        "phlegm dampness",
    ],
    "ama": ["toxicity", "metabolic toxin", "dampness toxin", "pathogenic toxin", "phlegm toxin"],
    "ojas": ["vital essence", "immunity"],
    "tejas": ["metabolic fire", "biological heat"],
    "prana": ["life force", "vital energy"],
}


class MappingTier(StrEnum):
    """Confidence tier of a mapping outcome."""

    DIRECT_TM2 = "direct_tm2"
    BIOMEDICAL = "biomedical"
    SEMANTIC = "semantic"
    UNMAPPABLE = "unmappable"


class MappingCandidate(BaseModel):
    """Raw candidate produced by search/heuristics prior to persistence."""

    source_code: str
    source_display: str
    source_system: str
    target_code: str
    target_display: str
    target_system: str
    target_definition: Optional[str] = None
    lexical_score: float = 0.0
    definition_score: float = 0.0
    synonym_score: float = 0.0
    category_score: float = 0.0
    validation_score: float = 0.0
    aggregate_score: float = 0.0
    tier: MappingTier = Field(default=MappingTier.UNMAPPABLE)
    equivalence: ConceptMapEquivalenceEnum = Field(
        default=ConceptMapEquivalenceEnum.UNMATCHED
    )
    evidence: Dict[str, Any] = Field(default_factory=dict)


class MappingRecord(MappingCandidate):
    """Persistable mapping record annotated with job metadata."""

    job_id: str
    namaste_release: str
    who_release: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MappingJobContext(BaseModel):
    """Contextual metadata applied to all records generated in a run."""

    job_id: str = Field(default_factory=lambda: uuid4().hex)
    namaste_release: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y%m%d")
    )
    who_release: str = Field(default_factory=lambda: settings.who_icd_api_version)
    run_started_at: datetime = Field(default_factory=datetime.utcnow)
    search_terms_per_code: int = Field(default=12)


class NamasteTerm(BaseModel):
    """Simplified representation of a NAMASTE CodeSystem concept."""

    code: str
    display: str
    definition: Optional[str] = None
    system_url: str = NAMASTE_SYSTEM_URI
    synonyms: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)


class MappingEngine:
    """Core service that orchestrates mapping between NAMASTE and ICD-11."""

    def __init__(self, db):
        self.db = db
        self._keyword_regex = re.compile(r"[^a-zA-Z0-9]+")
        self._category_hints = self._build_category_hints()
        self._max_candidates_per_term = 15

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def map_all_terms(
        self,
        terms: Sequence[NamasteTerm],
        job: MappingJobContext,
        force_refresh: bool = False,
    ) -> List[MappingRecord]:
        """Map all provided NAMASTE terms into ICD-11 counterparts.

        Args:
            terms: Iterable of NAMASTE concepts to map.
            job: Context describing this mapping run.
            force_refresh: If True, existing records for the job will be
                overwritten.
        Returns:
            List of mapping records ready for persistence.
        """

        logger.info("[MAPPING] Starting mapping job %s for %d terms", job.job_id, len(terms))

        if force_refresh:
            await self._purge_previous_results(job.job_id)

        all_records: List[MappingRecord] = []

        for term in terms:
            term_records = await self._map_single_term(term, job)
            all_records.extend(term_records)

        logger.info(
            "[MAPPING] Completed job %s, generated %d mapping records",
            job.job_id,
            len(all_records),
        )
        return all_records

    async def persist_records(self, records: Sequence[MappingRecord]) -> None:
        """Persist mapping records into ``code_mappings`` collection."""

        if not records:
            return

        operations = []
        for record in records:
            doc = record.model_dump()
            filter_query = {
                "source_system": doc.pop("source_system"),
                "source_code": doc.pop("source_code"),
                "target_system": doc.pop("target_system"),
                "target_code": doc.pop("target_code"),
            }
            created_at = doc.pop("created_at", record.created_at)
            doc.update(
                {
                    "source_system": filter_query["source_system"],
                    "source_code": filter_query["source_code"],
                    "target_system": filter_query["target_system"],
                    "target_code": filter_query["target_code"],
                }
            )
            operations.append(
                (
                    filter_query,
                    {"$set": doc, "$setOnInsert": {"created_at": created_at}},
                )
            )

        for filter_query, payload in operations:
            await self.db.code_mappings.update_one(
                filter_query,
                payload,
                upsert=True,
            )

    async def create_concept_map(
        self,
        records: Sequence[MappingRecord],
        job: MappingJobContext,
        concept_map_id: str = "namaste-who-dual-coding",
    ) -> ConceptMap:
        """Materialise mapping records as a FHIR ``ConceptMap`` resource."""

        groups: Dict[Tuple[str, str], ConceptMapGroup] = {}
        for record in records:
            key = (record.source_system, record.target_system)
            group = groups.get(key)
            if group is None:
                group = ConceptMapGroup(
                    source=record.source_system,
                    target=record.target_system,
                    element=[],
                )
                groups[key] = group

            group.element.append(
                ConceptMapElement(
                    code=record.source_code,
                    display=record.source_display,
                    target=[
                        ConceptMapTarget(
                            code=record.target_code,
                            display=record.target_display,
                            equivalence=record.equivalence,
                            comment=f"score={record.aggregate_score:.2f}; tier={record.tier}",
                        )
                    ],
                )
            )

        concept_map = ConceptMap(
            id=f"{concept_map_id}-{job.job_id}",
            url=f"{NAMASTE_SYSTEM_URI}/ConceptMap/{concept_map_id}/{job.job_id}",
            status="active",
            name="NAMASTEWHODualCodingConceptMap",
            title="NAMASTE ↔ ICD-11 Dual Coding ConceptMap",
            date=datetime.utcnow(),
            source=NAMASTE_SYSTEM_URI,
            target="http://id.who.int/icd/release/11",
            group=list(groups.values()),
        )

        return concept_map

    # ------------------------------------------------------------------
    # Core Mapping Logic
    # ------------------------------------------------------------------
    async def _map_single_term(
        self, term: NamasteTerm, job: MappingJobContext
    ) -> List[MappingRecord]:
        search_terms = self._build_search_terms(term)[: job.search_terms_per_code]
        logger.debug("[MAPPING] %s search terms: %s", term.code, search_terms)

        local_candidates = await self._search_local_index(term, search_terms)
        api_candidates = await self._search_who_api(term, search_terms)
        rule_candidates = self._semantic_bridges(term)

        combined = self._deduplicate_candidates(
            local_candidates + api_candidates + rule_candidates
        )

        validation_scores = await self._load_validation_scores(term.code)
        augmented_synonyms: List[str] = []
        seen_synonyms: set[str] = set()
        for syn in list(term.synonyms) + list(search_terms):
            if not syn:
                continue
            norm = syn.lower()
            if norm in seen_synonyms:
                continue
            seen_synonyms.add(norm)
            augmented_synonyms.append(syn)

        scored_candidates: List[MappingCandidate] = []
        for candidate in combined:
            self._score_candidate(
                term,
                candidate,
                validation_scores,
                term_synonyms=augmented_synonyms,
            )
            if candidate.aggregate_score < 0.35 and candidate.tier == MappingTier.UNMAPPABLE:
                continue
            scored_candidates.append(candidate)

        records = [
            MappingRecord(
                **candidate.model_dump(),
                job_id=job.job_id,
                namaste_release=job.namaste_release,
                who_release=job.who_release,
                created_at=datetime.utcnow(),
            )
            for candidate in scored_candidates
        ]
        return records

    async def _load_validation_scores(self, namaste_code: str) -> Dict[str, float]:
        cursor = self.db.mapping_validations.find({"namaste_code": namaste_code})
        results = await cursor.to_list(None)
        scores: Dict[str, float] = {}
        for doc in results:
            who_code = doc.get("who_code")
            score = doc.get("validation_score")
            if who_code and score is not None:
                existing = scores.get(who_code)
                if existing is None:
                    scores[who_code] = score
                else:
                    scores[who_code] = (existing + score) / 2
        return scores

    def _score_candidate(
        self,
        term: NamasteTerm,
        candidate: MappingCandidate,
        validation_scores: Dict[str, float],
        term_synonyms: Optional[Sequence[str]] = None,
    ) -> None:
        lexical = self._lexical_similarity(term.display, candidate.target_display)
        definition = self._definition_similarity(term.definition, candidate.target_definition)
        synonym_source = term_synonyms if term_synonyms is not None else term.synonyms
        synonym = self._synonym_similarity(synonym_source, candidate.target_display)
        category = self._category_alignment(term, candidate)
        validation = validation_scores.get(candidate.target_code, 0.0)

        candidate.lexical_score = lexical
        candidate.definition_score = definition
        candidate.synonym_score = synonym
        candidate.category_score = category
        candidate.validation_score = validation

        aggregate = (
            0.35 * lexical
            + 0.25 * definition
            + 0.20 * synonym
            + 0.15 * category
            + 0.05 * validation
        )
        if candidate.target_system == TM2_SYSTEM_URI:
            aggregate += 0.15 * synonym
            if synonym >= 0.4:
                aggregate = max(aggregate, 0.6)

        aggregate = min(max(aggregate, 0.0), 1.0)
        candidate.aggregate_score = aggregate

        if (
            candidate.target_system == TM2_SYSTEM_URI
            and synonym >= 0.4
            and aggregate >= 0.6
        ):
            candidate.tier = MappingTier.DIRECT_TM2
            candidate.equivalence = ConceptMapEquivalenceEnum.EQUIVALENT
        elif candidate.target_system == TM2_SYSTEM_URI and aggregate >= 0.7:
            candidate.tier = MappingTier.DIRECT_TM2
            candidate.equivalence = ConceptMapEquivalenceEnum.EQUIVALENT
        elif candidate.target_system == MMS_SYSTEM_URI and aggregate >= 0.6:
            candidate.tier = MappingTier.BIOMEDICAL
            candidate.equivalence = ConceptMapEquivalenceEnum.RELATEDTO
        elif candidate.target_system == SEMANTIC_SYSTEM_URI and aggregate >= 0.4:
            candidate.tier = MappingTier.SEMANTIC
            candidate.equivalence = ConceptMapEquivalenceEnum.NARROWER
        elif aggregate >= 0.35:
            candidate.tier = MappingTier.BIOMEDICAL
            candidate.equivalence = ConceptMapEquivalenceEnum.INEXACT
        else:
            candidate.tier = MappingTier.UNMAPPABLE
            candidate.equivalence = ConceptMapEquivalenceEnum.UNMATCHED

        candidate.evidence = {
            "lexical": lexical,
            "definition": definition,
            "synonym": synonym,
            "category": category,
            "validation": validation,
        }

    async def _search_local_index(
        self, term: NamasteTerm, search_terms: Sequence[str]
    ) -> List[MappingCandidate]:
        candidates: List[MappingCandidate] = []
        for text in search_terms:
            if not text:
                continue
            try:
                cursor = self.db.who_icd_codes.find(
                    {
                        "$text": {"$search": text},
                    },
                    {
                        "score": {"$meta": "textScore"},
                        "code": 1,
                        "title": 1,
                        "definition": 1,
                        "tm2_category": 1,
                        "linearization": 1,
                    },
                ).sort("score", {"$meta": "textScore"}).limit(5)
                docs = await cursor.to_list(None)
            except Exception as exc:  # pragma: no cover - safeguard for missing index
                logger.warning("Text search failed for '%s': %s", text, exc)
                docs = []

            for doc in docs:
                target_system = (
                    TM2_SYSTEM_URI
                    if doc.get("tm2_category")
                    else MMS_SYSTEM_URI
                )
                candidates.append(
                    MappingCandidate(
                        source_code=term.code,
                        source_display=term.display,
                        source_system=term.system_url,
                        target_code=doc.get("code"),
                        target_display=(doc.get("title", {}) or {}).get("@value")
                        or doc.get("title"),
                        target_definition=(
                            (doc.get("definition", {}) or {}).get("@value")
                            or doc.get("definition")
                        ),
                        target_system=target_system,
                    )
                )
        return candidates

    async def _search_who_api(
        self, term: NamasteTerm, search_terms: Sequence[str]
    ) -> List[MappingCandidate]:
        candidates: List[MappingCandidate] = []
        tm2_bucket: List[MappingCandidate] = []
        other_bucket: List[MappingCandidate] = []
        seen_codes: set[str] = set()

        for text in search_terms:
            if not text or len(text) < 3:
                continue
            try:
                response = await who_icd_client.search_entities(
                    term=text,
                    limit=10,
                    include_tm2_only=False,
                    chapter_filter="TM1,TM2",
                )
                entities = response.get("destinationEntities", [])
                if not entities:
                    response = await who_icd_client.search_entities(
                        term=text,
                        limit=10,
                        include_tm2_only=False,
                        chapter_filter=None,
                    )
                    entities = response.get("destinationEntities", [])
            except Exception as exc:
                logger.warning("WHO API search failed for '%s': %s", text, exc)
                continue

            for raw_entity in entities:
                entity = WHOICD11TM2Entity(raw_entity)
                target_code = entity.code or entity.entity_id
                if not target_code:
                    continue

                target_system = TM2_SYSTEM_URI if entity.is_tm2_related() else MMS_SYSTEM_URI
                candidate = MappingCandidate(
                    source_code=term.code,
                    source_display=term.display,
                    source_system=term.system_url,
                    target_code=target_code,
                    target_display=entity.display_title,
                    target_definition=entity.display_definition,
                    target_system=target_system,
                )
                if target_code in seen_codes:
                    continue
                seen_codes.add(target_code)
                if target_system == TM2_SYSTEM_URI:
                    tm2_bucket.append(candidate)
                else:
                    other_bucket.append(candidate)
            await asyncio.sleep(0.2)

        candidates.extend(tm2_bucket + other_bucket)
        return candidates

    def _semantic_bridges(self, term: NamasteTerm) -> List[MappingCandidate]:
        matches: List[MappingCandidate] = []
        bridges = {
            "vata": ("XK7G.0", "Traditional medicine constitutional pattern"),
            "pitta": ("XK7G.1", "Traditional medicine metabolic pattern"),
            "kapha": ("XK7G.2", "Traditional medicine structural pattern"),
            "ama": ("XK7G.3", "Traditional medicine toxic accumulation"),
            "ojas": ("XK7G.4", "Traditional medicine vital essence"),
            "tejas": ("XK7G.5", "Traditional medicine metabolic fire"),
            "prana": ("XK7G.6", "Traditional medicine life force"),
            "panchakarma": ("XK8Y.0", "Traditional medicine detoxification"),
            "rasayana": ("XK8Y.1", "Traditional medicine rejuvenation"),
            "vajikarana": ("XK8Y.2", "Traditional medicine fertility therapy"),
        }
        ascii_display = self._strip_diacritics(term.display.lower())
        normalized_display = self._normalize(ascii_display)
        for keyword, (code, display) in bridges.items():
            if keyword in ascii_display or keyword in normalized_display:
                matches.append(
                    MappingCandidate(
                        source_code=term.code,
                        source_display=term.display,
                        source_system=term.system_url,
                        target_code=code,
                        target_display=display,
                        target_system=SEMANTIC_SYSTEM_URI,
                        target_definition=display,
                    )
                )
        return matches

    def _deduplicate_candidates(
        self, candidates: Sequence[MappingCandidate]
    ) -> List[MappingCandidate]:
        deduped: Dict[str, MappingCandidate] = {}
        for candidate in candidates:
            if not candidate.target_code:
                continue
            if candidate.target_code in deduped:
                continue
            deduped[candidate.target_code] = candidate
            if len(deduped) >= self._max_candidates_per_term:
                break
        return list(deduped.values())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_category_hints(self) -> Dict[str, List[str]]:
        return {
            "ayurveda": [
                "dosha",
                "vata",
                "pitta",
                "kapha",
                "ama",
                "ojas",
                "wind",
                "heat",
                "dampness",
                "phlegm",
            ],
            "siddha": ["tamil", "siddha"],
            "unani": ["unani", "tibb", "mizaj"],
            "respiratory": ["shwasa", "kasa"],
            "metabolic": ["prameha", "madhumeha"],
            "mental": ["unmada", "apasmara"],
        }

    def _build_search_terms(self, term: NamasteTerm) -> List[str]:
        seeds: List[str] = [term.display]
        if term.definition:
            seeds.append(term.definition[:80])
        seeds.extend(term.synonyms[:5])
        seeds.extend(term.categories)
        seeds.extend(term.properties.values())

        bucket: List[str] = []
        seen: set[str] = set()

        for raw in seeds:
            if not raw:
                continue
            stripped = raw.strip()
            if not stripped:
                continue

            ascii_variant = self._strip_diacritics(stripped)
            for variant in {stripped, ascii_variant}:
                lowered = variant.lower()
                if not lowered or lowered in seen:
                    continue
                seen.add(lowered)
                bucket.append(variant)
                self._append_domain_synonyms(lowered, bucket)

        if any("dosha" in key for key in seen):
            bucket.extend(["vata dosha", "pitta dosha", "kapha dosha"])

        bucket.extend(["traditional medicine", "ayurveda"])

        deduped: List[str] = []
        dedup_seen: set[str] = set()
        for value in bucket:
            lowered = value.lower()
            if lowered in dedup_seen or len(lowered) < 3:
                continue
            dedup_seen.add(lowered)
            deduped.append(value)

        return deduped

    def _lexical_similarity(self, a: Optional[str], b: Optional[str]) -> float:
        if not a or not b:
            return 0.0
        norm_a = self._normalize(a)
        norm_b = self._normalize(b)
        if not norm_a or not norm_b:
            return 0.0

        tokens_a = set(norm_a.split())
        tokens_b = set(norm_b.split())
        if not tokens_a or not tokens_b:
            return 0.0

        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        jaccard = intersection / union if union else 0.0

        seq_ratio = self._sequence_ratio(norm_a, norm_b)
        return (jaccard + seq_ratio) / 2

    def _definition_similarity(self, a: Optional[str], b: Optional[str]) -> float:
        if not a or not b:
            return 0.0
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf = vectorizer.fit_transform([a, b])
        similarity_matrix = cosine_similarity(tfidf[0:1], tfidf[1:2])
        score = similarity_matrix[0][0]
        return min(max(score, 0.0), 1.0)

    def _synonym_similarity(self, synonyms: Sequence[str], target: Optional[str]) -> float:
        if not synonyms or not target:
            return 0.0
        target_norm = self._normalize(target)
        best = 0.0
        for synonym in synonyms:
            score = self._sequence_ratio(target_norm, self._normalize(synonym))
            best = max(best, score)
        return best

    def _category_alignment(
        self, term: NamasteTerm, candidate: MappingCandidate
    ) -> float:
        text = self._normalize(candidate.target_display)
        matches = 0
        total = 0
        for category, hints in self._category_hints.items():
            total += 1
            if any(hint in text for hint in hints) and any(
                hint in term.display.lower() for hint in hints
            ):
                matches += 1
        return matches / total if total else 0.0

    def _normalize(self, value: str) -> str:
        value = self._strip_diacritics(value.lower())
        value = self._keyword_regex.sub(" ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def _sequence_ratio(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        # Simple implementation of similarity using Dice coefficient
        bigrams_a = self._bigrams(a)
        bigrams_b = self._bigrams(b)
        if not bigrams_a or not bigrams_b:
            return 0.0
        intersection = len(set(bigrams_a) & set(bigrams_b))
        score = (2 * intersection) / (len(bigrams_a) + len(bigrams_b))
        return min(max(score, 0.0), 1.0)

    def _bigrams(self, text: str) -> List[str]:
        return [text[i : i + 2] for i in range(len(text) - 1)]

    def _strip_diacritics(self, value: str) -> str:
        return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")

    def _append_domain_synonyms(self, key: str, bucket: List[str]) -> None:
        compact = key.replace(" ", "")
        for trigger, synonyms in TRADITIONAL_TO_CLINICAL_SYNONYMS.items():
            if trigger in compact:
                bucket.extend(synonyms)

    async def _purge_previous_results(self, job_id: str) -> None:
        await self.db.code_mappings.delete_many({"job_id": job_id})

    # ------------------------------------------------------------------
    # Static factory methods
    # ------------------------------------------------------------------
    @staticmethod
    async def load_namaste_terms(db) -> List[NamasteTerm]:
        """Load all NAMASTE concepts from MongoDB into ``NamasteTerm`` objects."""

        query = {
            "$or": [
                {"url": {"$regex": "namaste", "$options": "i"}},
                {"id": {"$regex": "namaste", "$options": "i"}},
                {"name": {"$regex": "NAMASTE", "$options": "i"}},
            ]
        }
        cursor = db.codesystems.find(query)
        codesystems = await cursor.to_list(None)

        terms: List[NamasteTerm] = []
        seen_codes: set[str] = set()
        for codesystem in codesystems:
            system_url = codesystem.get("url") or NAMASTE_SYSTEM_URI
            for concept in codesystem.get("concept", []):
                code = concept.get("code")
                display = concept.get("display")
                if not code or not display:
                    continue
                if code in seen_codes:
                    continue
                seen_codes.add(code)

                definition = concept.get("definition")
                synonyms = MappingEngine._extract_synonyms(concept)
                categories = MappingEngine._extract_categories(concept)
                properties = {
                    prop.get("code"): prop.get("valueString")
                    for prop in concept.get("property", [])
                    if isinstance(prop, dict)
                }

                terms.append(
                    NamasteTerm(
                        code=code,
                        display=display,
                        definition=definition,
                        system_url=system_url,
                        synonyms=synonyms,
                        categories=categories,
                        properties=properties,
                    )
                )
        return terms

    @staticmethod
    def _extract_synonyms(concept: Dict[str, Any]) -> List[str]:
        synonyms: List[str] = []
        for designation in concept.get("designation", []) or []:
            value = designation.get("value") if isinstance(designation, dict) else None
            if value:
                synonyms.append(value)
        for prop in concept.get("property", []) or []:
            if isinstance(prop, dict) and prop.get("code") in {"diacritical", "devanagari", "arabic", "tamil"}:
                value = prop.get("valueString")
                if value:
                    synonyms.append(value)
        return synonyms

    @staticmethod
    def _extract_categories(concept: Dict[str, Any]) -> List[str]:
        categories: List[str] = []
        for prop in concept.get("property", []) or []:
            if not isinstance(prop, dict):
                continue
            code = prop.get("code", "").lower()
            value = prop.get("valueString") or prop.get("valueCode")
            if not value:
                continue
            if code in {"dosha", "category", "system"}:
                categories.append(value)
        return categories
