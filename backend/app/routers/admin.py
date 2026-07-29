"""
Admin Router

One endpoint: trigger a real, on-demand pull of NDMA's published bulletins.
This is what the frontend's sidebar "Refresh data" control calls — it is
NOT run silently in the background; the person has to press it, and the
button should show a busy state while this is in flight, since a full NDMA
crawl can take a while.

No auth here — this app has no login (by design, see product spec). If
this is ever deployed somewhere with public write access long-term, put
this behind a token check.
"""

import logging
from fastapi import APIRouter, HTTPException
from app.services.seeder import seed_database
from app.database import execute_query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/refresh-bulletins")
async def refresh_bulletins():
    """
    Re-run the full NDMA ingestion pipeline: crawl NDMA's published bulletin
    listings, parse whatever's currently posted, and upsert it into the
    database (existing records for the same county+month are updated in
    place; nothing is fabricated for counties NDMA hasn't published for).
    Forecasts are regenerated afterward from the refreshed data.
    """
    try:
        await seed_database()
    except Exception as e:
        logger.exception("Real data refresh failed")
        raise HTTPException(status_code=502, detail=f"NDMA refresh failed: {e}")

    stats = await execute_query(
        """SELECT COUNT(*) as total_records,
                  COUNT(DISTINCT county_id) as counties_covered,
                  MAX(parsed_at) as last_updated
           FROM bulletins""",
        fetchone=True,
    )
    return {
        "status": "ok",
        "total_records": stats["total_records"] if stats else 0,
        "counties_covered": stats["counties_covered"] if stats else 0,
        "last_updated": stats["last_updated"] if stats else None,
    }
