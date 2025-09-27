"""
Dashboard API routes
Provides endpoints for frontend dashboard metrics and health monitoring
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime, timedelta

from app.database import mongodb

router = APIRouter()


async def _average_response_time(hours: int = 24) -> float | None:
    """Compute average response time from performance metrics collection."""

    db = mongodb.database
    if db is None:
        return None

    window_start = datetime.utcnow() - timedelta(hours=hours)
    cursor = db.performance_metrics.find({"timestamp": {"$gte": window_start}})
    total_duration = 0.0
    count = 0
    async for doc in cursor:
        duration = doc.get("duration_ms") or doc.get("duration")
        if duration is None:
            continue
        try:
            total_duration += float(duration)
            count += 1
        except (TypeError, ValueError):
            continue
    if count == 0:
        return None
    return round(total_duration / count, 2)


async def _compute_success_rate(hours: int = 24) -> Dict[str, Any]:
    """Compute API success/error counts from performance metrics."""

    db = mongodb.database
    if db is None:
        return {"success": 0, "errors": 0, "success_rate": None}

    window_start = datetime.utcnow() - timedelta(hours=hours)
    cursor = db.performance_metrics.find({"timestamp": {"$gte": window_start}})
    success = 0
    errors = 0
    async for doc in cursor:
        status_code = doc.get("status_code")
        if status_code is None:
            continue
        try:
            code = int(status_code)
        except (TypeError, ValueError):
            continue
        if 200 <= code < 400:
            success += 1
        else:
            errors += 1
    total = success + errors
    success_rate = round((success / total) * 100, 2) if total else None
    return {"success": success, "errors": errors, "success_rate": success_rate}


@router.get("/health", tags=["Dashboard"])
async def get_system_health() -> Dict[str, Any]:
    """Get system health metrics for dashboard"""
    try:
        # Check database connectivity
        db_healthy = await mongodb.health_check()
        
        # Get collection counts
        db = mongodb.database
        codesystem_count = await db.codesystems.count_documents({}) if db else 0
        conceptmap_count = await db.conceptmaps.count_documents({}) if db else 0
        valueset_count = await db.valuesets.count_documents({}) if db else 0
        namaste_term_count = await db.namaste_codes.count_documents({}) if db else 0
        mapping_record_count = await db.code_mappings.count_documents({}) if db else 0
        who_code_count = await db.who_icd_codes.count_documents({}) if db else 0
        
        # Calculate uptime (approximation)
        if mongodb.connected_at:
            uptime_delta = datetime.utcnow() - mongodb.connected_at
            uptime_hours = round(uptime_delta.total_seconds() / 3600, 2)
        else:
            uptime_hours = None

        average_response = await _average_response_time()
        api_success = await _compute_success_rate()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy", 
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "connected" if db_healthy else "disconnected",
                "collections": {
                    "codesystems": codesystem_count,
                    "conceptmaps": conceptmap_count,
                    "valuesets": valueset_count,
                    "namaste_codes": namaste_term_count,
                    "code_mappings": mapping_record_count,
                    "who_icd_codes": who_code_count,
                }
            },
            "services": {
                "fhir_server": "running" if codesystem_count else "idle",
                "who_integration": "active" if who_code_count else "pending_seed",
                "namaste_mapping": "active" if mapping_record_count else "no_mappings",
                "authentication": "enabled" if (db and await db.abha_sessions.count_documents({}) > 0) else "idle",
            },
            "metrics": {
                "uptime_hours": uptime_hours,
                "total_codes": codesystem_count + valueset_count,
                "active_mappings": mapping_record_count,
                "response_time_ms": average_response,
                "api_success_rate": api_success["success_rate"],
                "api_calls_success": api_success["success"],
                "api_calls_errors": api_success["errors"],
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )


@router.get("/mapping-quality", tags=["Dashboard"])
async def get_mapping_quality_metrics() -> Dict[str, Any]:
    """Get mapping quality metrics for dashboard"""
    try:
        db = mongodb.database
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not initialised"
            )

        total_mappings = await db.code_mappings.count_documents({})
        mapped_terms = len(await db.code_mappings.distinct("source_code"))
        total_terms = await db.namaste_codes.count_documents({})
        completion_rate = (
            round((mapped_terms / total_terms) * 100, 1) if total_terms else 0.0
        )

        tier_pipeline = [
            {"$group": {"_id": "$tier", "count": {"$sum": 1}}},
        ]
        tier_counts = {
            doc["_id"] or "unknown": doc["count"]
            async for doc in db.code_mappings.aggregate(tier_pipeline)
        }

        score_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$aggregate_score"},
                    "high_confidence": {
                        "$sum": {
                            "$cond": [{"$gte": ["$aggregate_score", 0.75]}, 1, 0]
                        }
                    },
                }
            }
        ]
        score_cursor = db.code_mappings.aggregate(score_pipeline)
        score_stats = await score_cursor.to_list(length=1)
        avg_score = round(score_stats[0]["avg_score"], 3) if score_stats else None
        high_confidence = score_stats[0]["high_confidence"] if score_stats else 0

        validation_docs = db.mapping_validations.find({})
        validation_count = 0
        validation_sum = 0.0
        validation_failures = 0
        async for doc in validation_docs:
            score = doc.get("validation_score")
            if score is None:
                continue
            try:
                numeric_score = float(score)
            except (TypeError, ValueError):
                continue
            validation_sum += numeric_score
            validation_count += 1
            if numeric_score < 0.6:
                validation_failures += 1
        average_validation = (
            round(validation_sum / validation_count, 3)
            if validation_count
            else None
        )

        distribution_pipeline = [
            {"$group": {"_id": "$source_system", "count": {"$sum": 1}}}
        ]
        distribution_raw = {
            (doc["_id"] or "unknown").split("/")[-1]: doc["count"]
            async for doc in db.code_mappings.aggregate(distribution_pipeline)
        }

        latest_run = await db.mapping_runs.find_one(
            {},
            sort=[("completed_at", -1)],
        )

        last_completed_at = None
        if latest_run and latest_run.get("completed_at"):
            completed = latest_run.get("completed_at")
            if isinstance(completed, datetime):
                last_completed_at = completed.isoformat()

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        updates_today = await db.mapping_runs.count_documents(
            {"completed_at": {"$gte": today_start}}
        )

        api_success = await _compute_success_rate()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "mapping_stats": {
                "total_mappings": total_mappings,
                "mapped_terms": mapped_terms,
                "tier_breakdown": tier_counts,
                "completion_rate": completion_rate,
            },
            "quality_metrics": {
                "average_aggregate_score": avg_score,
                "high_confidence_mappings": high_confidence,
                "average_validation_score": average_validation,
                "validation_records": validation_count,
                "validation_failed": validation_failures,
            },
            "mapping_distribution": {
                "by_source_system": distribution_raw,
            },
            "recent_updates": {
                "last_run_id": latest_run.get("job_id") if latest_run else None,
                "last_completed_at": last_completed_at,
                "updates_today": updates_today,
                "api_success_rate": api_success["success_rate"],
                "api_errors_today": api_success["errors"],
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get mapping quality metrics: {str(e)}"
        )


@router.get("/statistics", tags=["Dashboard"])
async def get_dashboard_statistics() -> Dict[str, Any]:
    """Get general dashboard statistics"""
    try:
        db = mongodb.database
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not initialised"
            )

        codesystem_count = await db.codesystems.count_documents({})
        conceptmap_count = await db.conceptmaps.count_documents({})
        valueset_count = await db.valuesets.count_documents({})
        total_resources = codesystem_count + conceptmap_count + valueset_count

        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_codes_this_month = await db.code_mappings.count_documents(
            {"created_at": {"$gte": month_start}}
        )

        window_30 = now - timedelta(days=30)
        window_60 = now - timedelta(days=60)
        runs_last_30 = await db.mapping_runs.count_documents(
            {"completed_at": {"$gte": window_30}}
        )
        runs_prev_30 = await db.mapping_runs.count_documents(
            {
                "completed_at": {
                    "$lt": window_30,
                    "$gte": window_60,
                }
            }
        )
        if runs_prev_30:
            growth_rate = round(((runs_last_30 - runs_prev_30) / runs_prev_30) * 100, 2)
        else:
            growth_rate = 100.0 if runs_last_30 else 0.0

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        api_calls_today = await db.performance_metrics.count_documents(
            {"timestamp": {"$gte": today_start}}
        )
        average_response = await _average_response_time()
        api_success = await _compute_success_rate()

        run_types_cursor = db.mapping_runs.aggregate(
            [{"$group": {"_id": "$run_type"}}]
        )
        active_integrations = len([doc async for doc in run_types_cursor])

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "resource_counts": {
                "code_systems": codesystem_count,
                "concept_maps": conceptmap_count,
                "value_sets": valueset_count,
                "total_resources": total_resources
            },
            "growth_metrics": {
                "monthly_growth_rate": growth_rate,
                "new_codes_this_month": new_codes_this_month,
                "active_integrations": active_integrations,
            },
            "system_metrics": {
                "api_calls_today": api_calls_today,
                "average_response_time_ms": average_response,
                "success_rate": api_success["success_rate"],
                "error_rate": (
                    round(100 - api_success["success_rate"], 2)
                    if api_success["success_rate"] is not None
                    else None
                ),
                "success_count": api_success["success"],
                "error_count": api_success["errors"],
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard statistics: {str(e)}"
        )