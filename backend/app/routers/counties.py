"""
Counties API Router

Endpoints for county data, priority queue, and map data.
"""

import json
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.database import execute_query
from app.models import (
    CountyOut, CountyDetail, PriorityQueueItem, MapCountyData
)
from app.services.llm import generate_regional_synthesis

router = APIRouter(prefix="/api/counties", tags=["counties"])


@router.get("/", response_model=list[CountyOut])
async def list_counties(
    region: Optional[str] = Query(None, description="Filter by region"),
    livelihood_zone: Optional[str] = Query(None, description="Filter by livelihood zone"),
):
    """List all counties with their current status."""
    query = """
        SELECT c.id, c.name, c.region, c.livelihood_zone, c.latitude, c.longitude,
               b.phase as current_phase, b.vci3m as current_vci3m, b.spi as current_spi
        FROM counties c
        LEFT JOIN bulletins b ON b.county_id = c.id
            AND b.month = (SELECT MAX(month) FROM bulletins WHERE county_id = c.id)
    """
    params = []

    conditions = []
    if region:
        conditions.append("c.region = ?")
        params.append(region)
    if livelihood_zone:
        conditions.append("c.livelihood_zone = ?")
        params.append(livelihood_zone)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY c.name"

    rows = await execute_query(query, tuple(params))
    return [CountyOut(**row) for row in rows]


async def _priority_queue_data(
    phase: Optional[str] = None,
    region: Optional[str] = None,
    livelihood_zone: Optional[str] = None,
    sort_by: str = "priority_score",
    sort_order: str = "desc",
    limit: int = 47,
) -> list[PriorityQueueItem]:
    """
    Core priority-queue logic, factored out from the route so other
    endpoints (e.g. regional synthesis) can call it directly with plain
    Python arguments instead of through FastAPI's Query() defaults.
    """
    query = """
        SELECT c.id as county_id, c.name as county_name, c.region, c.livelihood_zone,
               b.phase as current_phase, b.vci3m as current_vci3m,
               f.forecast_values, f.crossing_date, f.crossing_phase,
               f.days_to_crossing, f.confidence, f.priority_score,
               f.ai_explanation as ai_summary
        FROM counties c
        LEFT JOIN bulletins b ON b.county_id = c.id
            AND b.month = (SELECT MAX(month) FROM bulletins WHERE county_id = c.id)
        LEFT JOIN forecasts f ON f.county_id = c.id
            AND f.generated_at = (SELECT MAX(generated_at) FROM forecasts WHERE county_id = c.id)
    """
    params = []
    # A priority queue must contain reported conditions, never placeholder
    # classifications for counties whose bulletin has not been published.
    conditions = ["b.id IS NOT NULL"]

    if phase:
        conditions.append("b.phase = ?")
        params.append(phase)
    if region:
        conditions.append("c.region = ?")
        params.append(region)
    if livelihood_zone:
        conditions.append("c.livelihood_zone = ?")
        params.append(livelihood_zone)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Sort
    valid_sorts = {"priority_score", "days_to_crossing", "current_vci3m", "county_name"}
    sort_field = sort_by if sort_by in valid_sorts else "priority_score"
    order = "DESC" if sort_order.lower() == "desc" else "ASC"

    if sort_field == "priority_score":
        query += f" ORDER BY COALESCE(f.priority_score, 0) {order}"
    elif sort_field == "days_to_crossing":
        query += f" ORDER BY COALESCE(f.days_to_crossing, 9999) {'ASC' if order == 'DESC' else 'DESC'}"
    elif sort_field == "current_vci3m":
        query += f" ORDER BY COALESCE(b.vci3m, 100) {'ASC' if order == 'DESC' else 'DESC'}"
    else:
        query += f" ORDER BY c.name {order}"

    query += " LIMIT ?"
    params.append(limit)

    rows = await execute_query(query, tuple(params))

    # Build priority queue items with sparkline data
    items = []
    for rank, row in enumerate(rows, 1):
        # Get sparkline data (last 6 months of VCI3M)
        sparkline_query = """
            SELECT vci3m FROM bulletins 
            WHERE county_id = ? AND vci3m IS NOT NULL
            ORDER BY month DESC LIMIT 6
        """
        sparkline_rows = await execute_query(sparkline_query, (row["county_id"],))
        sparkline = [r["vci3m"] for r in reversed(sparkline_rows)]

        # Add forecast values to sparkline
        forecast_values = json.loads(row["forecast_values"]) if row.get("forecast_values") else []
        forecast_vci3m = forecast_values[-1]["vci3m"] if forecast_values else None

        items.append(PriorityQueueItem(
            rank=rank,
            county_id=row["county_id"],
            county_name=row["county_name"],
            region=row["region"],
            livelihood_zone=row["livelihood_zone"],
            current_phase=row["current_phase"],
            current_vci3m=row.get("current_vci3m"),
            forecast_vci3m=forecast_vci3m,
            crossing_date=row.get("crossing_date"),
            crossing_phase=row.get("crossing_phase"),
            days_to_crossing=row.get("days_to_crossing"),
            confidence=row.get("confidence"),
            priority_score=row.get("priority_score") or 0.0,
            sparkline_data=sparkline,
            ai_summary=row.get("ai_summary"),
        ))

    return items


@router.get("/priority-queue", response_model=list[PriorityQueueItem])
async def get_priority_queue(
    phase: Optional[str] = Query(None, description="Filter by phase"),
    region: Optional[str] = Query(None, description="Filter by region"),
    livelihood_zone: Optional[str] = Query(None, description="Filter by livelihood zone"),
    sort_by: str = Query("priority_score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    limit: int = Query(47, description="Max results"),
):
    """
    Get the ranked priority queue of all counties.
    Returns counties sorted by priority score (urgency).
    """
    return await _priority_queue_data(
        phase=phase, region=region, livelihood_zone=livelihood_zone,
        sort_by=sort_by, sort_order=sort_order, limit=limit,
    )


@router.get("/regional-synthesis")
async def get_regional_synthesis():
    """AI cross-county pattern synthesis over the current priority queue."""
    queue = await _priority_queue_data(limit=47)
    return await generate_regional_synthesis([item.model_dump() for item in queue])


@router.get("/map-data", response_model=list[MapCountyData])
async def get_map_data():
    """Get county data formatted for the choropleth map."""
    query = """
        SELECT c.id as county_id, c.name as county_name,
               b.phase as current_phase, b.vci3m,
               f.crossing_phase as forecast_phase,
               f.days_to_crossing, f.priority_score
        FROM counties c
        LEFT JOIN bulletins b ON b.county_id = c.id
            AND b.month = (SELECT MAX(month) FROM bulletins WHERE county_id = c.id)
        LEFT JOIN forecasts f ON f.county_id = c.id
            AND f.generated_at = (SELECT MAX(generated_at) FROM forecasts WHERE county_id = c.id)
        ORDER BY c.name
    """
    rows = await execute_query(query)
    return [MapCountyData(
        county_id=r["county_id"],
        county_name=r["county_name"],
        current_phase=r.get("current_phase"),
        forecast_phase=r.get("forecast_phase"),
        days_to_crossing=r.get("days_to_crossing"),
        priority_score=r.get("priority_score"),
        vci3m=r.get("vci3m"),
    ) for r in rows]


@router.get("/{county_id}", response_model=CountyDetail)
async def get_county_detail(county_id: int):
    """Get detailed data for a single county."""
    county = await execute_query(
        """SELECT c.id, c.name, c.region, c.livelihood_zone, c.latitude, c.longitude,
                  b.phase as current_phase, b.vci3m as current_vci3m, b.spi as current_spi
           FROM counties c
           LEFT JOIN bulletins b ON b.county_id = c.id
               AND b.month = (SELECT MAX(month) FROM bulletins WHERE county_id = c.id)
           WHERE c.id = ?""",
        (county_id,),
        fetchone=True
    )

    if not county:
        raise HTTPException(status_code=404, detail="County not found")

    # Historical data
    historical = await execute_query(
        """SELECT month, vci3m, spi, phase, source_url, source_page
           FROM bulletins WHERE county_id = ? ORDER BY month ASC""",
        (county_id,)
    )

    # Latest forecast
    forecast_row = await execute_query(
        """SELECT * FROM forecasts WHERE county_id = ?
           ORDER BY generated_at DESC LIMIT 1""",
        (county_id,),
        fetchone=True
    )

    forecast = None
    ai_explanation = None
    if forecast_row:
        forecast = {
            "generated_at": forecast_row["generated_at"],
            "forecast_weeks": forecast_row["forecast_weeks"],
            "forecast_values": json.loads(forecast_row["forecast_values"]) if forecast_row["forecast_values"] else [],
            "crossing_date": forecast_row.get("crossing_date"),
            "crossing_phase": forecast_row.get("crossing_phase"),
            "days_to_crossing": forecast_row.get("days_to_crossing"),
            "confidence": forecast_row.get("confidence"),
            "priority_score": forecast_row.get("priority_score"),
        }
        ai_explanation = forecast_row.get("ai_explanation")

    return CountyDetail(
        id=county["id"],
        name=county["name"],
        region=county["region"],
        livelihood_zone=county["livelihood_zone"],
        latitude=county.get("latitude"),
        longitude=county.get("longitude"),
        current_phase=county.get("current_phase"),
        current_vci3m=county.get("current_vci3m"),
        current_spi=county.get("current_spi"),
        historical=historical,
        forecast=forecast,
        ai_explanation=ai_explanation,
    )


@router.get("/regions/list")
async def list_regions():
    """Get unique regions for filtering."""
    rows = await execute_query("SELECT DISTINCT region FROM counties ORDER BY region")
    return [r["region"] for r in rows]


@router.get("/livelihood-zones/list")
async def list_livelihood_zones():
    """Get unique livelihood zones for filtering."""
    rows = await execute_query(
        "SELECT DISTINCT livelihood_zone FROM counties ORDER BY livelihood_zone"
    )
    return [r["livelihood_zone"] for r in rows]
