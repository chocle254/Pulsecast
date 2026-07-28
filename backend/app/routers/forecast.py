"""
Forecast API Router

Endpoints for generating and retrieving forecasts,
and for the backtest / track record panel.
"""

import json
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.database import execute_query, get_db
from app.models import ForecastOut, BacktestRecord, BacktestSummary
from app.services.forecast import generate_county_forecast
from app.services.llm import generate_explanation

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/{county_id}", response_model=ForecastOut)
async def get_forecast(county_id: int):
    """Get the latest forecast for a county."""
    forecast = await execute_query(
        """SELECT f.*, c.name as county_name
           FROM forecasts f
           JOIN counties c ON c.id = f.county_id
           WHERE f.county_id = ?
           ORDER BY f.generated_at DESC LIMIT 1""",
        (county_id,),
        fetchone=True
    )
    
    if not forecast:
        raise HTTPException(status_code=404, detail="No forecast found for this county")
    
    forecast_values = json.loads(forecast["forecast_values"]) if forecast["forecast_values"] else []
    
    return ForecastOut(
        county_id=forecast["county_id"],
        county_name=forecast["county_name"],
        generated_at=forecast["generated_at"],
        forecast_weeks=forecast["forecast_weeks"],
        forecast_values=forecast_values,
        crossing_date=forecast.get("crossing_date"),
        crossing_phase=forecast.get("crossing_phase"),
        days_to_crossing=forecast.get("days_to_crossing"),
        confidence=forecast.get("confidence"),
        priority_score=forecast.get("priority_score"),
        ai_explanation=forecast.get("ai_explanation"),
    )


@router.post("/{county_id}/regenerate")
async def regenerate_forecast(county_id: int):
    """Regenerate the forecast for a specific county."""
    # Get historical data
    historical = await execute_query(
        """SELECT vci3m, phase FROM bulletins 
           WHERE county_id = ? AND vci3m IS NOT NULL
           ORDER BY month ASC""",
        (county_id,)
    )
    
    if not historical:
        raise HTTPException(status_code=404, detail="No historical data for this county")
    
    vci3m_series = [r["vci3m"] for r in historical]
    current_phase = historical[-1]["phase"]
    
    forecast = generate_county_forecast(
        county_id=county_id,
        historical_vci3m=vci3m_series,
        current_phase=current_phase
    )
    
    # Save to database
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO forecasts 
               (county_id, generated_at, forecast_weeks, forecast_values,
                crossing_date, crossing_phase, days_to_crossing,
                confidence, priority_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (county_id, forecast["generated_at"], forecast["forecast_weeks"],
             json.dumps(forecast["forecast_values"]),
             forecast.get("crossing_date"),
             forecast.get("crossing_phase"),
             forecast.get("days_to_crossing"),
             forecast.get("confidence"),
             forecast.get("priority_score"))
        )
        await db.commit()
    finally:
        await db.close()
    
    return forecast


@router.get("/{county_id}/explain")
async def get_explanation(
    county_id: int,
    detail_level: str = Query("full", description="summary or full")
):
    """Generate an AI explanation for a county's forecast."""
    # Get county + forecast data
    county = await execute_query(
        """SELECT c.name, b.phase, b.vci3m, b.spi
           FROM counties c
           LEFT JOIN bulletins b ON b.county_id = c.id
               AND b.month = (SELECT MAX(month) FROM bulletins WHERE county_id = c.id)
           WHERE c.id = ?""",
        (county_id,),
        fetchone=True
    )
    
    if not county:
        raise HTTPException(status_code=404, detail="County not found")
    
    forecast = await execute_query(
        """SELECT * FROM forecasts WHERE county_id = ?
           ORDER BY generated_at DESC LIMIT 1""",
        (county_id,),
        fetchone=True
    )
    
    forecast_values = []
    crossing_date = None
    crossing_phase = None
    days_to_crossing = None
    confidence = None
    priority_score = 0
    
    if forecast:
        forecast_values = json.loads(forecast["forecast_values"]) if forecast["forecast_values"] else []
        crossing_date = forecast.get("crossing_date")
        crossing_phase = forecast.get("crossing_phase")
        days_to_crossing = forecast.get("days_to_crossing")
        confidence = forecast.get("confidence")
        priority_score = forecast.get("priority_score", 0)
    
    result = await generate_explanation(
        county_name=county["name"],
        current_phase=county.get("phase") or "Normal",
        current_vci3m=county.get("vci3m"),
        current_spi=county.get("spi"),
        forecast_values=forecast_values,
        crossing_date=crossing_date,
        crossing_phase=crossing_phase,
        days_to_crossing=days_to_crossing,
        confidence=confidence,
        priority_score=priority_score,
        detail_level=detail_level
    )
    
    # Cache the explanation
    if forecast:
        db = await get_db()
        try:
            await db.execute(
                "UPDATE forecasts SET ai_explanation = ? WHERE id = ?",
                (result["explanation"], forecast["id"])
            )
            await db.commit()
        finally:
            await db.close()
    
    return {
        "county_id": county_id,
        "county_name": county["name"],
        **result
    }


# --- Backtest endpoints ---

@router.get("/backtest/summary", response_model=BacktestSummary)
async def get_backtest_summary():
    """
    Get aggregate backtest statistics.
    
    Compares each month's forecast (generated from prior months' data)
    against the actual phase reported in the following bulletin.
    """
    # For the seeded data, we generate backtests by comparing
    # what AR(2) would have predicted at month N-1 vs actual at month N
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT c.id as county_id, c.name as county_name
            FROM counties c
            ORDER BY c.name
        """)
        counties = [dict(r) for r in await cursor.fetchall()]
        
        total = 0
        correct = 0
        false_alarms = 0
        county_results = []
        
        for county in counties:
            cursor = await db.execute(
                """SELECT month, vci3m, phase FROM bulletins
                   WHERE county_id = ? AND vci3m IS NOT NULL
                   ORDER BY month ASC""",
                (county["county_id"],)
            )
            rows = [dict(r) for r in await cursor.fetchall()]
            
            if len(rows) < 4:
                continue
            
            county_total = 0
            county_correct = 0
            county_false_alarms = 0
            
            # For each month after the first 3, compare backtest
            for i in range(3, len(rows)):
                historical = [r["vci3m"] for r in rows[:i]]
                actual_phase = rows[i]["phase"]
                
                # Generate what forecast would have been
                from app.services.parser import classify_from_vci3m
                from app.services.forecast import forecast_vci3m
                
                predicted_values = forecast_vci3m(historical, weeks=4)
                if predicted_values:
                    predicted_vci3m = predicted_values[-1]["vci3m"]
                    predicted_phase = classify_from_vci3m(predicted_vci3m)
                else:
                    predicted_phase = rows[i-1]["phase"]
                    predicted_vci3m = rows[i-1]["vci3m"]
                
                hit = (predicted_phase == actual_phase)
                total += 1
                county_total += 1
                
                if hit:
                    correct += 1
                    county_correct += 1
                else:
                    from app.services.parser import get_phase_severity
                    if get_phase_severity(predicted_phase) > get_phase_severity(actual_phase):
                        false_alarms += 1
                        county_false_alarms += 1
            
            if county_total > 0:
                county_results.append({
                    "county_id": county["county_id"],
                    "county_name": county["county_name"],
                    "total": county_total,
                    "correct": county_correct,
                    "hit_rate": round(county_correct / county_total, 3),
                    "false_alarms": county_false_alarms,
                })
        
        return BacktestSummary(
            total_predictions=total,
            correct_predictions=correct,
            hit_rate=round(correct / total, 3) if total > 0 else 0,
            false_alarm_rate=round(false_alarms / total, 3) if total > 0 else 0,
            counties=county_results,
        )
    finally:
        await db.close()


@router.get("/backtest/{county_id}")
async def get_county_backtest(county_id: int):
    """Get per-month backtest data for a specific county."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT b.month, b.vci3m, b.phase, c.name as county_name
               FROM bulletins b
               JOIN counties c ON c.id = b.county_id
               WHERE b.county_id = ? AND b.vci3m IS NOT NULL
               ORDER BY b.month ASC""",
            (county_id,)
        )
        rows = [dict(r) for r in await cursor.fetchall()]
        
        if len(rows) < 4:
            return {"county_id": county_id, "records": [], "summary": {}}
        
        records = []
        for i in range(3, len(rows)):
            historical = [r["vci3m"] for r in rows[:i]]
            actual_phase = rows[i]["phase"]
            actual_vci3m = rows[i]["vci3m"]
            
            from app.services.parser import classify_from_vci3m
            from app.services.forecast import forecast_vci3m
            
            predicted_values = forecast_vci3m(historical, weeks=4)
            if predicted_values:
                predicted_vci3m = predicted_values[-1]["vci3m"]
                predicted_phase = classify_from_vci3m(predicted_vci3m)
            else:
                predicted_phase = rows[i-1]["phase"]
                predicted_vci3m = rows[i-1]["vci3m"]
            
            records.append(BacktestRecord(
                county_id=county_id,
                county_name=rows[0]["county_name"],
                month=rows[i]["month"],
                predicted_phase=predicted_phase,
                actual_phase=actual_phase,
                predicted_vci3m=round(predicted_vci3m, 1),
                actual_vci3m=round(actual_vci3m, 1),
                hit=(predicted_phase == actual_phase),
            ))
        
        total = len(records)
        correct = sum(1 for r in records if r.hit)
        
        return {
            "county_id": county_id,
            "county_name": rows[0]["county_name"],
            "records": [r.model_dump() for r in records],
            "summary": {
                "total": total,
                "correct": correct,
                "hit_rate": round(correct / total, 3) if total > 0 else 0,
            }
        }
    finally:
        await db.close()
