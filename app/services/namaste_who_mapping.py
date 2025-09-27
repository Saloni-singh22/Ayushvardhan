"""NAMASTE ↔ WHO ICD-11 mapping orchestration service."""

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List

import logging

from app.database import get_database
from app.services.mapping_engine import (
    MappingEngine,
    MappingJobContext,
    MappingRecord,
    NamasteTerm,
)

logger = logging.getLogger(__name__)


class NAMASTEWHOMappingService:
    """High-level façade coordinating the mapping engine + persistence."""

    def __init__(self) -> None:
        self._engine: MappingEngine | None = None

    async def create_comprehensive_mapping(
        self, *, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Run full mapping workflow and persist results.

        Args:
            force_refresh: When ``True`` existing records for the job are cleared
                before persistence.
        Returns:
            Summary dictionary with statistics and persisted resource identifiers.
        """

        db = await get_database()
        engine = self._get_engine(db)

        namaste_terms = await MappingEngine.load_namaste_terms(db)
        if not namaste_terms:
            logger.warning("[MAPPING] No NAMASTE terms found. Aborting mapping run.")
            return {
                "terms_processed": 0,
                "records_created": 0,
                "tier_breakdown": {},
                "job_id": None,
                "concept_map_id": None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        job = MappingJobContext()
        records = await engine.map_all_terms(
            namaste_terms,
            job,
            force_refresh=force_refresh,
        )

        await engine.persist_records(records)
        concept_map = await engine.create_concept_map(records, job)
        concept_map_doc = concept_map.model_dump(by_alias=True)
        concept_map_doc["job_id"] = job.job_id
        concept_map_doc["mapping_timestamp"] = datetime.utcnow()

        await db.conceptmaps.replace_one(
            {"id": concept_map.id},
            concept_map_doc,
            upsert=True,
        )

        await self._store_mapping_run(db, job, namaste_terms, records, concept_map.id)

        summary = self._build_summary(job, namaste_terms, records, concept_map.id)
        logger.info("[MAPPING] Job %s summary: %s", job.job_id, summary)
        return summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_engine(self, db) -> MappingEngine:
        if self._engine is None:
            self._engine = MappingEngine(db)
        return self._engine

    async def _store_mapping_run(
        self,
        db,
        job: MappingJobContext,
        terms: List[NamasteTerm],
        records: List[MappingRecord],
        concept_map_id: str,
    ) -> None:
        tier_counts = Counter(record.tier for record in records)
        doc = {
            "job_id": job.job_id,
            "namaste_release": job.namaste_release,
            "who_release": job.who_release,
            "terms_processed": len(terms),
            "records_created": len(records),
            "tier_breakdown": dict(tier_counts),
            "started_at": job.run_started_at,
            "completed_at": datetime.utcnow(),
            "concept_map_id": concept_map_id,
        }
        await db.mapping_runs.replace_one(
            {"job_id": job.job_id},
            doc,
            upsert=True,
        )

        metadata_doc = {
            "_id": "namaste_who_mapping_metadata",
            "last_job_id": job.job_id,
            "terms_processed": len(terms),
            "records_created": len(records),
            "tier_breakdown": dict(tier_counts),
            "last_updated": datetime.utcnow(),
            "concept_map_id": concept_map_id,
        }
        await db.mapping_metadata.replace_one(
            {"_id": "namaste_who_mapping_metadata"},
            metadata_doc,
            upsert=True,
        )

    def _build_summary(
        self,
        job: MappingJobContext,
        terms: List[NamasteTerm],
        records: List[MappingRecord],
        concept_map_id: str,
    ) -> Dict[str, Any]:
        tier_counts = Counter(record.tier for record in records)
        avg_score = (
            sum(record.aggregate_score for record in records) / len(records)
            if records
            else 0.0
        )
        best_examples = self._extract_best_examples(records)
        return {
            "job_id": job.job_id,
            "namaste_release": job.namaste_release,
            "who_release": job.who_release,
            "terms_processed": len(terms),
            "records_created": len(records),
            "tier_breakdown": {tier: count for tier, count in tier_counts.items()},
            "average_score": round(avg_score, 3),
            "concept_map_id": concept_map_id,
            "timestamp": datetime.utcnow().isoformat(),
            "high_confidence_examples": best_examples,
        }

    def _extract_best_examples(
        self, records: List[MappingRecord], limit: int = 5
    ) -> List[Dict[str, Any]]:
        top_records = sorted(records, key=lambda r: r.aggregate_score, reverse=True)[:limit]
        return [
            {
                "source_code": record.source_code,
                "source_display": record.source_display,
                "target_code": record.target_code,
                "target_display": record.target_display,
                "tier": record.tier,
                "score": round(record.aggregate_score, 3),
            }
            for record in top_records
        ]


namaste_who_mapping_service = NAMASTEWHOMappingService()