"""
Backtest-Based Confidence Calibration

The original confidence figure attached to a forecasted threshold crossing
was a fixed heuristic — `max(0.3, 1.0 - week * 0.08)` — with no connection
to how accurate this app's own forecasts have actually been. This module
replaces that anchor with the empirical hit-rate measured by the same
backtest methodology already used in the /backtest/summary endpoint: for
every county, at every point in its bulletin history, replay what a
4-week-ahead forecast built from bulletins[:i] would have predicted, and
check it against what bulletins[i] actually confirmed.

When there isn't enough backtest history yet to trust the estimate (e.g.
right after a fresh seed), this falls back to a conservative prior instead
of calibrating off a handful of samples.
"""

import logging
from typing import Optional

from app.database import get_db
from app.services.forecast import forecast_vci3m
from app.services.parser import classify_from_vci3m

logger = logging.getLogger(__name__)

MIN_SAMPLES_TO_TRUST = 10
DEFAULT_PRIOR_HIT_RATE = 0.65  # used until there's enough backtest history to calibrate from


async def compute_confidence_calibration() -> dict:
    """
    Returns:
        {
            "hit_rate": float,        # empirical accuracy to anchor confidence to
            "sample_size": int,       # how many backtest predictions this is based on
            "calibrated": bool,       # False if we fell back to the default prior
        }
    """
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM counties")
        county_ids = [row["id"] for row in await cursor.fetchall()]

        total = 0
        correct = 0

        for county_id in county_ids:
            cursor = await db.execute(
                """SELECT vci3m, phase FROM bulletins
                   WHERE county_id = ? AND vci3m IS NOT NULL
                   ORDER BY month ASC""",
                (county_id,),
            )
            rows = [dict(r) for r in await cursor.fetchall()]
            if len(rows) < 4:
                continue

            for i in range(3, len(rows)):
                historical = [r["vci3m"] for r in rows[:i]]
                actual_phase = rows[i]["phase"]

                predicted_values = forecast_vci3m(historical, weeks=4)
                if not predicted_values:
                    continue
                predicted_phase = classify_from_vci3m(predicted_values[-1]["vci3m"])

                total += 1
                if predicted_phase == actual_phase:
                    correct += 1

        if total < MIN_SAMPLES_TO_TRUST:
            logger.info(
                "Only %s backtest samples available (need %s) — using default prior (%.0f%%) for confidence calibration",
                total, MIN_SAMPLES_TO_TRUST, DEFAULT_PRIOR_HIT_RATE * 100,
            )
            return {
                "hit_rate": DEFAULT_PRIOR_HIT_RATE,
                "sample_size": total,
                "calibrated": False,
            }

        hit_rate = correct / total
        logger.info(
            "Confidence calibration: %.1f%% empirical hit rate over %s backtest samples",
            hit_rate * 100, total,
        )
        return {
            "hit_rate": round(hit_rate, 3),
            "sample_size": total,
            "calibrated": True,
        }
    finally:
        await db.close()
