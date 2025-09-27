"""
Enhanced NAMASTE-WHO Multi-Tier Mapping API Endpoints
Handles the reality that most NAMASTE terms won't have direct WHO TM2 matches
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from app.services.enhanced_namaste_who_mapping import enhanced_namaste_who_mapping_service
from app.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enhanced-mapping", tags=["Enhanced NAMASTE-WHO Mapping"])


@router.post("/create-multi-tier",
            summary="Create Multi-Tier NAMASTE ↔ WHO Mapping",
            description="Realistic approach: Handle limited WHO TM2 coverage with hierarchical fallback strategy")
async def create_multi_tier_mapping(
    background_tasks: BackgroundTasks,
    force_refresh: bool = Query(False, description="Force refresh of existing mappings")
):
    """
    Create comprehensive multi-tier mapping between NAMASTE and WHO systems
    
    This implements a realistic multi-tier approach:
    
    Tier 1: Direct WHO TM2 mapping (10-15% coverage)
    - Search for exact traditional medicine matches in WHO TM2
    - High confidence, ideal for traditional medicine EMRs
    
    Tier 2: Biomedical ICD-11 mapping (60-70% coverage) 
    - Map to equivalent biomedical conditions
    - Insurance-compatible, clinical decision support
    
    Tier 3: Semantic bridge mapping (10-20% coverage)
    - Custom categories for traditional concepts
    - Research and analytics purposes
    
    Tier 4: Unmappable documentation (5-10% coverage)
    - Preserve traditional knowledge
    - Input for future WHO TM expansion
    
    Args:
        force_refresh: Whether to refresh existing mappings
    
    Returns:
        Task information and mapping statistics
    """
    try:
        logger.info("Starting enhanced multi-tier mapping process")
        
        # Run mapping in background
        background_tasks.add_task(
            enhanced_namaste_who_mapping_service.create_enhanced_mapping,
            force_refresh
        )
        
        return {
            "task": "enhanced_multi_tier_mapping",
            "status": "started",
            "description": "Multi-tier mapping process handles limited WHO TM2 coverage with intelligent fallback",
            "tiers": {
                "tier_1": "Direct WHO TM2 mapping (highest confidence)",
                "tier_2": "Biomedical ICD-11 mapping (insurance compatible)",
                "tier_3": "Semantic bridge mapping (conceptual grouping)",
                "tier_4": "Unmappable documentation (future WHO expansion)"
            },
            "expected_coverage": {
                "who_tm2_direct": "10-15%",
                "biomedical_equivalent": "60-70%", 
                "semantic_bridge": "10-20%",
                "unmappable": "5-10%"
            },
            "parameters": {
                "force_refresh": force_refresh
            },
            "timestamp": datetime.now().isoformat(),
            "note": "Check /enhanced-mapping/status for progress and results"
        }
        
    except Exception as e:
        logger.error(f"Failed to start enhanced mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mapping initiation failed: {str(e)}")


@router.get("/status",
           summary="Get Enhanced Mapping Status",
           description="Check the status and results of multi-tier mapping process")
async def get_enhanced_mapping_status():
    """
    Get comprehensive status and statistics of the enhanced mapping process
    
    Returns detailed analysis including:
    - Tier distribution (how terms were mapped)
    - Confidence scoring analysis
    - Insurance compatibility metrics
    - Clinical recommendations
    
    Returns:
        Comprehensive mapping status and analytics
    """
    try:
        db = await get_database()
        latest_run = await db.mapping_runs.find_one(
            {"run_type": "enhanced_multi_tier"},
            sort=[("completed_at", -1)],
        )

        if not latest_run:
            return {
                "status": "pending",
                "mapping_type": "multi_tier_enhanced",
                "summary": {
                    "message": "No enhanced mapping runs recorded yet. Trigger /enhanced-mapping/create-multi-tier to generate analytics."
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        validations_total = await db.mapping_validations.count_documents({})
        latest_validation_doc = await db.mapping_validations.find_one(
            {}, sort=[("timestamp", -1)]
        )
        latest_validation = None
        if latest_validation_doc:
            latest_validation = {
                "namaste_code": latest_validation_doc.get("namaste_code"),
                "who_code": latest_validation_doc.get("who_code"),
                "validation_score": latest_validation_doc.get("validation_score"),
                "reviewer_id": latest_validation_doc.get("reviewer_id"),
                "timestamp": latest_validation_doc.get("timestamp").isoformat()
                if isinstance(latest_validation_doc.get("timestamp"), datetime)
                else latest_validation_doc.get("timestamp"),
            }

        return {
            "status": "completed",
            "mapping_type": "multi_tier_enhanced",
            "summary": {
                "job_id": latest_run.get("job_id"),
                "terms_processed": latest_run.get("terms_processed"),
                "average_confidence": latest_run.get("average_confidence"),
                "direct_tm2_matches": latest_run.get("direct_tm2_matches"),
                "biomedical_matches": latest_run.get("biomedical_matches"),
                "completed_at": latest_run.get("completed_at").isoformat() if latest_run.get("completed_at") else None,
            },
            "tier_distribution": latest_run.get("tier_breakdown", {}),
            "statistics": latest_run.get("statistics", {}),
            "validations": {
                "total_records": validations_total,
                "last_submission": latest_validation,
            },
            "next_steps": [
                "Review most recent run statistics",
                "Collect additional clinical validations",
                "Monitor tier distribution trends via /enhanced-mapping/analytics",
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get enhanced mapping status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")


@router.get("/analytics",
           summary="Get Mapping Analytics Dashboard",
           description="Comprehensive analytics on NAMASTE-WHO mapping performance")
async def get_mapping_analytics():
    """
    Get detailed analytics on mapping performance and coverage
    
    Provides insights for:
    - Clinical decision making
    - System optimization
    - WHO collaboration opportunities
    - Research and policy support
    
    Returns:
        Comprehensive mapping analytics
    """
    try:
        db = await get_database()

        total_records = await db.enhanced_mappings.count_documents({})
        tier_pipeline = [
            {"$group": {"_id": "$mapping_tier", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        tier_breakdown: Dict[str, int] = {}
        async for doc in db.enhanced_mappings.aggregate(tier_pipeline):
            key = doc["_id"] or "unknown"
            tier_breakdown[key] = doc["count"]

        confidence_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_confidence": {"$avg": "$confidence"},
                    "max_confidence": {"$max": "$confidence"},
                    "min_confidence": {"$min": "$confidence"},
                }
            }
        ]
        confidence_cursor = db.enhanced_mappings.aggregate(confidence_pipeline)
        confidence_doc = await confidence_cursor.to_list(length=1)
        confidence_stats = confidence_doc[0] if confidence_doc else {}

        validation_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_validation": {"$avg": "$validation_score"},
                    "count": {"$sum": 1},
                }
            }
        ]
        validation_cursor = db.mapping_validations.aggregate(validation_pipeline)
        validation_doc = await validation_cursor.to_list(length=1)
        validation_stats = validation_doc[0] if validation_doc else {}

        run_history_cursor = (
            db.mapping_runs.find({"run_type": "enhanced_multi_tier"})
            .sort("completed_at", -1)
            .limit(5)
        )
        run_history = []
        async for doc in run_history_cursor:
            run_history.append(
                {
                    "job_id": doc.get("job_id"),
                    "completed_at": doc.get("completed_at").isoformat() if doc.get("completed_at") else None,
                    "average_confidence": doc.get("average_confidence"),
                    "terms_processed": doc.get("terms_processed"),
                    "direct_tm2_matches": doc.get("direct_tm2_matches"),
                    "biomedical_matches": doc.get("biomedical_matches"),
                }
            )

        latest_statistics = run_history[0] if run_history else None

        return {
            "analytics_type": "enhanced_mapping_performance",
            "summary": {
                "total_records": total_records,
                "tier_breakdown": tier_breakdown,
                "average_confidence": round(confidence_stats.get("avg_confidence", 0.0), 3) if confidence_stats else None,
                "validation_average": round(validation_stats.get("avg_validation", 0.0), 3) if validation_stats else None,
                "validation_count": validation_stats.get("count", 0) if validation_stats else 0,
            },
            "confidence": {
                "average": round(confidence_stats.get("avg_confidence", 0.0), 3) if confidence_stats else None,
                "highest": confidence_stats.get("max_confidence") if confidence_stats else None,
                "lowest": confidence_stats.get("min_confidence") if confidence_stats else None,
            },
            "coverage_analysis": {
                "tier_distribution": tier_breakdown,
                "latest_run": latest_statistics,
            },
            "quality_metrics": {
                "validation_average": round(validation_stats.get("avg_validation", 0.0), 3) if validation_stats else None,
                "validation_records": validation_stats.get("count", 0) if validation_stats else 0,
            },
            "run_history": run_history,
            "recommendations": {
                "immediate": "Prioritise review of unmappable terms identified in latest run",
                "short_term": "Expand clinical validations for biomedical-tier mappings",
                "long_term": "Monitor confidence trends and adjust synonym corpus",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get mapping analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analytics retrieval failed: {str(e)}")


@router.get("/tier-distribution",
           summary="Get Mapping Tier Distribution",
           description="Detailed breakdown of how NAMASTE terms were mapped across different tiers")
async def get_tier_distribution():
    """
    Get detailed tier distribution showing mapping strategy effectiveness
    
    Returns:
        Tier-wise mapping distribution and analysis
    """
    try:
        db = await get_database()
        tier_pipeline = [
            {"$group": {"_id": "$mapping_tier", "count": {"$sum": 1}, "avg_confidence": {"$avg": "$confidence"}}},
            {"$sort": {"count": -1}},
        ]
        tiers: List[Dict[str, Any]] = []
        async for item in db.enhanced_mappings.aggregate(tier_pipeline):
            tiers.append(item)

        total = sum(item["count"] for item in tiers)
        tier_analysis = {}
        for item in tiers:
            tier_key = item["_id"] or "unknown"
            percentage = (item["count"] / total * 100) if total else 0
            tier_analysis[tier_key] = {
                "count": item["count"],
                "percentage": round(percentage, 2),
                "average_confidence": round(item.get("avg_confidence", 0.0), 3),
            }

        return {
            "tier_analysis": tier_analysis,
            "total_records": total,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get tier distribution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Tier analysis failed: {str(e)}")


@router.post("/validate-mapping",
            summary="Clinical Validation of Mapping Results",
            description="Submit clinical expert validation for mapping accuracy improvement")
async def validate_mapping(
    namaste_code: str,
    who_code: str,
    validation_score: float = Query(..., ge=0.0, le=1.0),
    clinical_notes: Optional[str] = None,
    reviewer_id: Optional[str] = None
):
    """
    Submit clinical validation for mapping accuracy
    
    Enables continuous improvement through expert feedback
    
    Args:
        namaste_code: NAMASTE term code
        who_code: WHO mapped code  
        validation_score: Expert confidence score (0.0-1.0)
        clinical_notes: Expert clinical notes
        reviewer_id: Validator identification
    
    Returns:
        Validation submission confirmation
    """
    try:
        db = await get_database()
        timestamp = datetime.utcnow()
        validation_doc = {
            "namaste_code": namaste_code,
            "who_code": who_code,
            "validation_score": validation_score,
            "clinical_notes": clinical_notes,
            "reviewer_id": reviewer_id,
            "timestamp": timestamp,
        }

        result = await db.mapping_validations.insert_one(validation_doc)

        return {
            "status": "validation_submitted",
            "validation_id": str(result.inserted_id),
            "data": {
                **validation_doc,
                "timestamp": timestamp.isoformat(),
            },
            "impact": "Validation will improve future mapping accuracy",
            "note": "Thank you for contributing to mapping quality improvement",
        }
        
    except Exception as e:
        logger.error(f"Failed to submit mapping validation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation submission failed: {str(e)}")


# Additional utility endpoints for enhanced mapping

@router.get("/search-suggestions/{namaste_term}",
           summary="Get WHO Search Suggestions for NAMASTE Term", 
           description="Get intelligent WHO search suggestions for better mapping")
async def get_search_suggestions(namaste_term: str):
    """
    Get intelligent search suggestions for improving NAMASTE-WHO mapping
    
    Args:
        namaste_term: NAMASTE term to find WHO equivalents for
    
    Returns:
        Suggested WHO search terms and strategies
    """
    try:
        # This would use the enhanced mapping service to generate suggestions
        suggestions = {
            "original_term": namaste_term,
            "clinical_synonyms": ["Generated from clinical_synonyms mapping"],
            "semantic_categories": ["Based on semantic_bridges"],
            "search_strategies": [
                "Direct traditional medicine search",
                "Biomedical symptom search", 
                "Conceptual category search"
            ],
            "recommended_approach": "Multi-tier search with fallback strategies"
        }
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Failed to get search suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search suggestions failed: {str(e)}")