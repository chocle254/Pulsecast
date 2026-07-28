"""
Forecasting Engine

Per-county autoregressive (AR) model for VCI3M projection, following
the validated approach in Barrett et al., 2020.

Produces 4–6 week VCI3M forecasts with confidence intervals and
detects threshold crossings into worse NDMA phases.
"""

import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from app.services.parser import VCI3M_THRESHOLDS, classify_from_vci3m, get_phase_severity

logger = logging.getLogger(__name__)


def fit_ar_model(series: list[float], order: int = 2) -> dict:
    """
    Fit a simple autoregressive model of given order.
    
    Uses Yule-Walker equations for parameter estimation.
    Returns model coefficients, intercept, and residual variance.
    """
    n = len(series)
    if n < order + 2:
        # Not enough data — return a naive model (random walk)
        return {
            "coefficients": [1.0] + [0.0] * (order - 1),
            "intercept": 0.0,
            "residual_variance": np.var(series) if len(series) > 1 else 25.0,
            "order": order,
            "method": "naive"
        }
    
    y = np.array(series)
    
    try:
        # Build AR design matrix
        X = np.zeros((n - order, order))
        for i in range(order):
            X[:, i] = y[order - i - 1:n - i - 1]
        
        Y = y[order:]
        
        # Add intercept
        X_with_intercept = np.column_stack([np.ones(X.shape[0]), X])
        
        # OLS estimation
        beta = np.linalg.lstsq(X_with_intercept, Y, rcond=None)[0]
        
        intercept = beta[0]
        coefficients = beta[1:].tolist()
        
        # Residuals
        predictions = X_with_intercept @ beta
        residuals = Y - predictions
        residual_variance = float(np.var(residuals))
        
        return {
            "coefficients": coefficients,
            "intercept": float(intercept),
            "residual_variance": max(residual_variance, 1.0),
            "order": order,
            "method": "ols"
        }
        
    except (np.linalg.LinAlgError, ValueError) as e:
        logger.warning(f"AR model fitting failed: {e}, using naive model")
        return {
            "coefficients": [0.95] + [0.0] * (order - 1),
            "intercept": float(np.mean(series) * 0.05),
            "residual_variance": float(np.var(series)) if len(series) > 1 else 25.0,
            "order": order,
            "method": "fallback"
        }


def forecast_vci3m(
    historical: list[float],
    weeks: int = 6,
    confidence_level: float = 0.90
) -> list[dict]:
    """
    Generate VCI3M forecast with confidence intervals.
    
    Args:
        historical: List of historical VCI3M values (chronological order)
        weeks: Number of weeks to forecast
        confidence_level: Confidence level for intervals (default 90%)
        
    Returns:
        List of {week, vci3m, lower, upper} forecast points
    """
    if not historical or len(historical) < 2:
        # Can't forecast without data
        return []
    
    model = fit_ar_model(historical, order=min(2, len(historical) - 1))
    
    coefficients = model["coefficients"]
    intercept = model["intercept"]
    residual_var = model["residual_variance"]
    order = model["order"]
    
    # Z-score for confidence interval
    from scipy import stats as scipy_stats
    try:
        z = scipy_stats.norm.ppf((1 + confidence_level) / 2)
    except ImportError:
        z = 1.645  # ~90% confidence
    
    # Generate forecasts
    recent = list(historical[-order:])
    forecasts = []
    cumulative_var = 0.0
    
    for week in range(1, weeks + 1):
        # AR prediction
        pred = intercept
        for i, coeff in enumerate(coefficients):
            idx = len(recent) - 1 - i
            if idx >= 0:
                pred += coeff * recent[idx]
        
        # Clamp to valid VCI range
        pred = max(0.0, min(100.0, pred))
        
        # Accumulate forecast uncertainty
        cumulative_var += residual_var
        std = np.sqrt(cumulative_var)
        
        lower = max(0.0, pred - z * std)
        upper = min(100.0, pred + z * std)
        
        forecasts.append({
            "week": week,
            "vci3m": round(float(pred), 1),
            "lower": round(float(lower), 1),
            "upper": round(float(upper), 1)
        })
        
        recent.append(pred)
    
    return forecasts


def detect_threshold_crossing(
    current_vci3m: float,
    current_phase: str,
    forecast_values: list[dict],
    base_date: Optional[datetime] = None
) -> dict:
    """
    Detect when a forecast crosses into a worse phase.
    
    Returns:
        {crossing_date, crossing_phase, days_to_crossing, confidence}
    """
    if not forecast_values:
        return {
            "crossing_date": None,
            "crossing_phase": None,
            "days_to_crossing": None,
            "confidence": None
        }
    
    base = base_date or datetime.now()
    current_severity = get_phase_severity(current_phase)
    
    # Check each forecast point for threshold crossings
    for point in forecast_values:
        forecast_phase = classify_from_vci3m(point["vci3m"])
        forecast_severity = get_phase_severity(forecast_phase)
        
        if forecast_severity > current_severity:
            crossing_date = base + timedelta(weeks=point["week"])
            days = point["week"] * 7
            
            # Confidence decreases with forecast horizon and uncertainty
            band_width = point["upper"] - point["lower"]
            base_confidence = max(0.3, 1.0 - (point["week"] * 0.08))
            
            # Adjust confidence based on how far into the threshold the forecast goes
            threshold = VCI3M_THRESHOLDS.get(current_phase, VCI3M_THRESHOLDS["Normal"])
            distance_past = threshold - point["vci3m"]
            margin_factor = min(1.0, max(0.5, distance_past / (band_width + 1)))
            
            confidence = round(base_confidence * margin_factor, 2)
            
            return {
                "crossing_date": crossing_date.strftime("%Y-%m-%d"),
                "crossing_phase": forecast_phase,
                "days_to_crossing": days,
                "confidence": confidence
            }
    
    # No crossing detected
    return {
        "crossing_date": None,
        "crossing_phase": None,
        "days_to_crossing": None,
        "confidence": None
    }


def calculate_priority_score(
    current_phase: str,
    days_to_crossing: Optional[int],
    confidence: Optional[float],
    current_vci3m: Optional[float] = None
) -> float:
    """
    Calculate priority score: severity × time-urgency × confidence.
    
    Higher score = higher priority (needs attention first).
    """
    # Severity component (0-4)
    severity = get_phase_severity(current_phase)
    
    if days_to_crossing is None or confidence is None:
        # No crossing detected — base priority on current severity
        return round(severity * 10.0, 1)
    
    # Time urgency (inversely proportional to days — sooner = more urgent)
    max_days = 42  # 6 weeks
    time_urgency = max(0.1, 1.0 - (days_to_crossing / max_days))
    
    # Combine: severity weight + time urgency + confidence
    # Counties about to cross into worse phases get boosted
    crossing_boost = 2.0 if days_to_crossing <= 14 else 1.0  # Extra urgency for 2-week horizon
    
    score = (severity + 1) * 20 * time_urgency * confidence * crossing_boost
    
    # VCI3M proximity bonus
    if current_vci3m is not None:
        for phase, threshold in sorted(VCI3M_THRESHOLDS.items(), key=lambda x: x[1]):
            if current_vci3m < threshold + 5:  # Within 5 points of a threshold
                score += 10
                break
    
    return round(max(0.0, min(100.0, score)), 1)


def generate_county_forecast(
    county_id: int,
    historical_vci3m: list[float],
    current_phase: str,
    forecast_weeks: int = 6
) -> dict:
    """
    Generate a complete forecast for a single county.
    
    Returns forecast values, crossing detection, priority score,
    and all metadata needed for the API response.
    """
    if not historical_vci3m:
        return {
            "county_id": county_id,
            "forecast_values": [],
            "crossing_date": None,
            "crossing_phase": None,
            "days_to_crossing": None,
            "confidence": None,
            "priority_score": 0.0,
        }
    
    current_vci3m = historical_vci3m[-1]
    
    # Generate forecast
    forecast_values = forecast_vci3m(historical_vci3m, weeks=forecast_weeks)
    
    # Detect crossing
    crossing = detect_threshold_crossing(
        current_vci3m, current_phase, forecast_values
    )
    
    # Calculate priority
    priority = calculate_priority_score(
        current_phase,
        crossing["days_to_crossing"],
        crossing["confidence"],
        current_vci3m
    )
    
    return {
        "county_id": county_id,
        "generated_at": datetime.now().isoformat(),
        "forecast_weeks": forecast_weeks,
        "forecast_values": forecast_values,
        "crossing_date": crossing["crossing_date"],
        "crossing_phase": crossing["crossing_phase"],
        "days_to_crossing": crossing["days_to_crossing"],
        "confidence": crossing["confidence"],
        "priority_score": priority,
    }
