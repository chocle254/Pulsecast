"""
Data Seeder Service

Generates realistic baseline data for all 47 Kenyan counties when
real NDMA bulletin data is not yet available. Uses known patterns:
- ASAL counties trend drier (lower VCI3M)
- Seasonal patterns (long rains Mar-May, short rains Oct-Dec)
- Regional clustering of drought conditions
"""

import json
import random
import math
import logging
from datetime import datetime, timedelta
from app.database import get_db, init_db
from app.services.ingestion import ALL_COUNTIES
from app.services.parser import classify_from_vci3m, VCI3M_THRESHOLDS
from app.services.forecast import generate_county_forecast

logger = logging.getLogger(__name__)

# Seed for reproducibility
random.seed(42)


def generate_seasonal_vci3m(
    base_level: float,
    months: int = 12,
    volatility: float = 8.0,
    seasonal_amplitude: float = 12.0,
    trend: float = 0.0
) -> list[dict]:
    """
    Generate a realistic VCI3M time series with seasonal patterns.
    
    Kenya's rainfall seasons:
    - Long rains: March–May (vegetation peaks ~June-July)
    - Short rains: October–December (vegetation peaks ~Jan-Feb)
    - Dry seasons: January–February, June–September
    """
    series = []
    now = datetime.now()
    
    for i in range(months):
        month_offset = months - 1 - i
        dt = now - timedelta(days=month_offset * 30)
        month = dt.month
        
        # Seasonal component (bimodal for Kenya)
        # Peak after long rains (~June, month=6) and short rains (~January, month=1)
        seasonal = (
            seasonal_amplitude * 0.6 * math.sin(2 * math.pi * (month - 7) / 12) +
            seasonal_amplitude * 0.4 * math.sin(2 * math.pi * (month - 1) / 6)
        )
        
        # Trend component
        trend_component = trend * i
        
        # Random walk noise
        noise = random.gauss(0, volatility)
        
        # Compute VCI3M
        vci3m = base_level + seasonal + trend_component + noise
        vci3m = max(5.0, min(95.0, vci3m))
        
        # SPI correlates loosely with VCI3M
        spi = (vci3m - 50) / 20 + random.gauss(0, 0.3)
        spi = max(-3.5, min(3.5, spi))
        
        series.append({
            "month": dt.strftime("%Y-%m"),
            "vci3m": round(vci3m, 1),
            "spi": round(spi, 2),
            "phase": classify_from_vci3m(vci3m)
        })
    
    return series


def get_county_baseline(county: dict) -> dict:
    """
    Determine baseline VCI3M level and volatility based on county characteristics.
    """
    livelihood = county.get("livelihood", "mixed")
    region = county.get("region", "")
    
    # Pastoralist areas trend drier
    if livelihood == "pastoralist":
        base = random.uniform(25, 45)
        vol = random.uniform(8, 15)
        trend = random.uniform(-1.5, 0.5)
    elif livelihood == "agro-pastoralist":
        base = random.uniform(35, 55)
        vol = random.uniform(6, 12)
        trend = random.uniform(-1.0, 0.5)
    else:
        base = random.uniform(45, 70)
        vol = random.uniform(4, 8)
        trend = random.uniform(-0.5, 0.5)
    
    # Regional adjustments
    if region in ("North Eastern",):
        base -= 10
        vol += 3
    elif region in ("Coast",):
        base -= 3
    elif region in ("Central", "Western"):
        base += 5
    
    return {"base": base, "volatility": vol, "trend": trend}


async def seed_database():
    """
    Seed the database with realistic data for all 47 counties.
    """
    await init_db()
    
    db = await get_db()
    try:
        # Check if already seeded
        cursor = await db.execute("SELECT COUNT(*) as count FROM counties")
        row = await cursor.fetchone()
        if row and dict(row)["count"] > 0:
            logger.info("Database already seeded, skipping")
            return
        
        logger.info("Seeding database with county data...")
        
        # Insert counties
        for county in ALL_COUNTIES:
            await db.execute(
                """INSERT INTO counties (name, region, livelihood_zone, latitude, longitude)
                   VALUES (?, ?, ?, ?, ?)""",
                (county["name"], county["region"], county["livelihood"],
                 county["lat"], county["lon"])
            )
        
        await db.commit()
        
        # Generate and insert historical bulletins
        cursor = await db.execute("SELECT id, name, region, livelihood_zone FROM counties")
        counties = [dict(row) for row in await cursor.fetchall()]
        
        now = datetime.now()
        
        for county in counties:
            baseline = get_county_baseline({
                "livelihood": county["livelihood_zone"],
                "region": county["region"]
            })
            
            series = generate_seasonal_vci3m(
                base_level=baseline["base"],
                months=12,
                volatility=baseline["volatility"],
                trend=baseline["trend"]
            )
            
            for record in series:
                await db.execute(
                    """INSERT OR IGNORE INTO bulletins 
                       (county_id, month, vci3m, spi, phase, source_url, parsed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (county["id"], record["month"], record["vci3m"], record["spi"],
                     record["phase"], "seeded-data", now.isoformat())
                )
            
            # Generate and cache forecast
            vci3m_series = [r["vci3m"] for r in series]
            current_phase = series[-1]["phase"]
            
            forecast = generate_county_forecast(
                county_id=county["id"],
                historical_vci3m=vci3m_series,
                current_phase=current_phase,
                forecast_weeks=6
            )
            
            await db.execute(
                """INSERT INTO forecasts 
                   (county_id, generated_at, forecast_weeks, forecast_values,
                    crossing_date, crossing_phase, days_to_crossing, 
                    confidence, priority_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (county["id"], forecast["generated_at"], forecast["forecast_weeks"],
                 json.dumps(forecast["forecast_values"]),
                 forecast.get("crossing_date"),
                 forecast.get("crossing_phase"),
                 forecast.get("days_to_crossing"),
                 forecast.get("confidence"),
                 forecast.get("priority_score"))
            )
        
        await db.commit()
        logger.info(f"Seeded {len(counties)} counties with historical data and forecasts")
        
    finally:
        await db.close()


async def regenerate_forecasts():
    """Re-run the forecasting engine for all counties using current data."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT c.id, c.name, c.livelihood_zone
            FROM counties c
        """)
        counties = [dict(row) for row in await cursor.fetchall()]
        
        for county in counties:
            # Get historical VCI3M values
            cursor = await db.execute(
                """SELECT vci3m, phase FROM bulletins 
                   WHERE county_id = ? ORDER BY month ASC""",
                (county["id"],)
            )
            rows = [dict(r) for r in await cursor.fetchall()]
            
            if not rows:
                continue
            
            vci3m_series = [r["vci3m"] for r in rows if r["vci3m"] is not None]
            current_phase = rows[-1]["phase"]
            
            forecast = generate_county_forecast(
                county_id=county["id"],
                historical_vci3m=vci3m_series,
                current_phase=current_phase
            )
            
            # Update or insert forecast
            await db.execute(
                """INSERT OR REPLACE INTO forecasts 
                   (county_id, generated_at, forecast_weeks, forecast_values,
                    crossing_date, crossing_phase, days_to_crossing,
                    confidence, priority_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (county["id"], forecast["generated_at"], forecast["forecast_weeks"],
                 json.dumps(forecast["forecast_values"]),
                 forecast.get("crossing_date"),
                 forecast.get("crossing_phase"),
                 forecast.get("days_to_crossing"),
                 forecast.get("confidence"),
                 forecast.get("priority_score"))
            )
        
        await db.commit()
        logger.info(f"Regenerated forecasts for {len(counties)} counties")
        
    finally:
        await db.close()
