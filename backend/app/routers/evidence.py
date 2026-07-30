"""
Evidence Trail API Router

Endpoints for the credibility screen — every parsed bulletin value
with source links.
"""

from fastapi import APIRouter, Query
from typing import Optional
from app.database import execute_query
from app.models import BulletinRecord

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("/", response_model=list[BulletinRecord])
async def get_evidence_trail(
    county_id: Optional[int] = Query(None, description="Filter by county"),
    month: Optional[str] = Query(None, description="Filter by month (YYYY-MM)"),
    phase: Optional[str] = Query(None, description="Filter by phase"),
    limit: int = Query(500, description="Max results"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """
    Get the full evidence trail — every parsed bulletin record
    with source references.
    """
    query = """
        SELECT b.id, b.county_id, c.name as county_name,
               b.month, b.vci3m, b.spi, b.phase,
               b.source_url, b.source_page, b.parsed_at,
               b.parsing_method, b.ai_evidence
        FROM bulletins b
        JOIN counties c ON c.id = b.county_id
    """
    params = []
    conditions = []
    
    if county_id:
        conditions.append("b.county_id = ?")
        params.append(county_id)
    if month:
        conditions.append("b.month = ?")
        params.append(month)
    if phase:
        conditions.append("b.phase = ?")
        params.append(phase)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY b.month DESC, c.name ASC"
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = await execute_query(query, tuple(params))
    return [BulletinRecord(**row) for row in rows]


@router.get("/months")
async def get_available_months():
    """Get list of months with data."""
    rows = await execute_query(
        "SELECT DISTINCT month FROM bulletins ORDER BY month DESC"
    )
    return [r["month"] for r in rows]


@router.get("/stats")
async def get_evidence_stats():
    """Get statistics about the evidence trail."""
    total = await execute_query(
        "SELECT COUNT(*) as count FROM bulletins", fetchone=True
    )
    months = await execute_query(
        "SELECT COUNT(DISTINCT month) as count FROM bulletins", fetchone=True
    )
    counties = await execute_query(
        "SELECT COUNT(DISTINCT county_id) as count FROM bulletins", fetchone=True
    )
    
    phase_dist = await execute_query(
        "SELECT phase, COUNT(*) as count FROM bulletins GROUP BY phase ORDER BY count DESC"
    )

    parsing_method_dist = await execute_query(
        "SELECT parsing_method, COUNT(*) as count FROM bulletins GROUP BY parsing_method"
    )

    last_updated = await execute_query(
        "SELECT MAX(parsed_at) as ts FROM bulletins", fetchone=True
    )

    return {
        "total_records": total["count"] if total else 0,
        "months_covered": months["count"] if months else 0,
        "counties_covered": counties["count"] if counties else 0,
        "phase_distribution": phase_dist,
        "parsing_method_distribution": parsing_method_dist,
        "last_updated": last_updated["ts"] if last_updated else None,
    }
