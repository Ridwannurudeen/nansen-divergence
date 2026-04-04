"""API v1 — performance endpoints."""
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get("/performance")
def get_performance(days: int | None = Query(None)):
    from nansen_divergence.history import get_performance_stats
    return get_performance_stats(days=days)


@router.get("/performance/by-phase")
def get_performance_by_phase():
    from nansen_divergence.history import get_performance_stats
    return get_performance_stats().get("by_phase", {})
