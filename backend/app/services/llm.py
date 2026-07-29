"""
LLM Translation Service

Converts quantitative forecasts into plain-language, cited guidance.
Uses Groq's OpenAI-compatible API with a currently supported model.

Every generated sentence references the actual indicator values behind it.
"""

import json
import re
import logging
from datetime import datetime
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a drought early-warning analyst for Kenya's National Drought Management Authority (NDMA). Your role is to translate quantitative drought forecasts into clear, actionable guidance for county drought coordinators.

CRITICAL RULES:
1. Every claim must cite the specific data value it's based on, using [ref:field_name=value] format
2. Use plain language a county coordinator would understand — no jargon without explanation
3. Be honest about uncertainty — if confidence is low, say so clearly
4. Frame findings in terms of NDMA's official 5-phase system (Normal → Alert → Alarm → Emergency → Recovery)
5. Make recommendations specific to the timeframe and severity
6. Tailor guidance to the county's livelihood zone: pastoralist zones depend on livestock and grazing, agro-pastoralist zones depend on crops and grazing together, mixed zones lean more toward settled farming and markets. State what the forecast specifically implies for that zone — not a generic recommendation that would apply anywhere.
7. When an ICPAC seasonal rainfall outlook is provided alongside the statistical forecast, reconcile the two explicitly. If they agree, say so and note it strengthens confidence in the forecast. If they disagree, flag the disagreement plainly and recommend treating the forecast as lower-confidence until the next bulletin — never silently pick one signal over the other.
8. Never overclaim accuracy — this is a proof-of-concept forecast, not an official NDMA classification
9. Keep it concise — 3-5 sentences maximum for summaries, up to 4 short paragraphs for detailed explanations

FORMATTING:
- Use [ref:VCI3M=XX.X] for VCI3M citations
- Use [ref:SPI=X.XX] for SPI citations
- Use [ref:phase=Phase] for phase citations
- Use [ref:crossing=YYYY-MM-DD] for crossing date citations
- Use [ref:confidence=XX%] for confidence citations
- Use [ref:seasonal_outlook=<period, e.g. Aug-Oct2026>] when citing the ICPAC seasonal outlook — cite the period only, describe its content in your own words in the prose"""


BACKTEST_SYSTEM_PROMPT = """You are a drought-forecasting model auditor reviewing Pulsecast's AR(2) backtest results against official NDMA bulletin classifications. Your job is pattern analysis across counties and months, not per-county advice.

CRITICAL RULES:
1. Every claim must cite the specific data value it's based on, using [ref:field_name=value] format
2. Identify patterns: which counties the model misses most, whether false alarms cluster in a livelihood zone, region, or phase transition type
3. Be honest about small sample sizes — if total_predictions is low, say the pattern is tentative, not conclusive
4. Never inflate the model's performance — if hit rate is mediocre or the sample is thin, say so plainly
5. Keep it to 2-3 short paragraphs
6. This is diagnostic writing for the model's own credibility page — treat it like a methods-section audit, not marketing copy"""


REGIONAL_SYSTEM_PROMPT = """You are a regional drought-risk analyst reviewing Pulsecast's current priority queue across all monitored counties. Your job is to spot clustering — counties in the same region or livelihood zone trending toward the same phase at once — which a per-county view can't surface on its own.

CRITICAL RULES:
1. Cite every county/phase claim using [ref:CountyName=Phase] format
2. Only report clusters that are actually present in the data — do not infer regional causes not stated in the input
3. If fewer than 3 counties currently show elevated phases (Alert/Alarm/Emergency), say clustering can't be assessed yet rather than forcing a pattern
4. Keep it to 2 short paragraphs
5. This informs the Disaster Response Team persona specifically — write for someone deciding whether to treat this as isolated county issues or a regional event"""


async def call_groq_api(messages: list[dict], max_tokens: int = 500) -> str:
    """
    Call the Groq API (OpenAI-compatible) for LLM inference.
    Groq offers an OpenAI-compatible chat-completions API.
    Falls back to NVIDIA NIM API if Groq key is unavailable.
    """
    api_key = settings.GROQ_API_KEY
    base_url = "https://api.groq.com/openai/v1/chat/completions"
    model = settings.LLM_MODEL

    # Try NVIDIA NIM as fallback
    if not api_key and settings.NVIDIA_API_KEY:
        api_key = settings.NVIDIA_API_KEY
        base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        model = "meta/llama-3.1-70b-instruct"

    if not api_key:
        raise ValueError("No LLM API key configured (set GROQ_API_KEY or NVIDIA_API_KEY)")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(base_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def generate_explanation(
    county_name: str,
    current_phase: str,
    current_vci3m: Optional[float],
    current_spi: Optional[float],
    forecast_values: list[dict],
    crossing_date: Optional[str],
    crossing_phase: Optional[str],
    days_to_crossing: Optional[int],
    confidence: Optional[float],
    priority_score: float,
    historical_trend: Optional[str] = None,
    detail_level: str = "summary",
    livelihood_zone: Optional[str] = None,
    seasonal_outlook: Optional[dict] = None
) -> dict:
    """
    Generate a plain-language explanation of a county's forecast.

    Args:
        detail_level: "summary" (1-2 sentences for queue) or "full" (detailed for county page)
        livelihood_zone: "pastoralist" / "agro-pastoralist" / "mixed" — drives the
            livelihood-specific guidance section instead of a static frontend template
        seasonal_outlook: optional dict from app.services.seasonal_outlook.fetch_seasonal_outlook()
            — a second, independent signal the model reconciles against the statistical forecast

    Returns:
        {explanation, citations, generated_at, model}
    """
    context = {
        "county": county_name,
        "livelihood_zone": livelihood_zone,
        "current_phase": current_phase,
        "current_vci3m": current_vci3m,
        "current_spi": current_spi,
        "forecast_end_vci3m": forecast_values[-1]["vci3m"] if forecast_values else None,
        "forecast_end_lower": forecast_values[-1]["lower"] if forecast_values else None,
        "forecast_end_upper": forecast_values[-1]["upper"] if forecast_values else None,
        "crossing_date": crossing_date,
        "crossing_phase": crossing_phase,
        "days_to_crossing": days_to_crossing,
        "confidence": f"{confidence*100:.0f}%" if confidence else None,
        "priority_score": priority_score,
        "historical_trend": historical_trend,
        "seasonal_outlook": (
            {
                "period": seasonal_outlook["period"],
                "rainfall_outlook": seasonal_outlook["rainfall_outlook"],
            }
            if seasonal_outlook else None
        ),
    }

    if detail_level == "summary":
        user_prompt = f"""Generate a ONE-SENTENCE summary for the priority queue for {county_name} county.

Data: {json.dumps(context, indent=2)}

The sentence should convey: current status, what's coming, and urgency. If seasonal_outlook is present and disagrees with the statistical forecast, briefly flag that. Include [ref:] citations for key values."""
    else:
        user_prompt = f"""Generate a detailed explanation (2-4 short paragraphs) for {county_name} county's drought forecast.

Data: {json.dumps(context, indent=2)}

Structure:
1. Current situation — what phase, what the indicators show
2. Forecast — what's projected, when any threshold crossing might happen, confidence level
3. If seasonal_outlook is present, reconcile it explicitly with the statistical forecast — do they agree or disagree, and what that means for how much to trust this forecast right now
4. Livelihood-specific guidance — given this county's livelihood_zone, what a coordinator should specifically prioritize (livestock, grazing and water for pastoralist zones; crops, food stocks and soil moisture for agro-pastoralist zones; markets and settled farming for mixed zones)

Include [ref:] citations for every specific value mentioned, including the seasonal outlook if present."""

    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        explanation = await call_groq_api(
            messages,
            max_tokens=500 if detail_level == "summary" else 1000
        )

        # Extract citations from the explanation
        citation_pattern = r'\[ref:(\w+)=([^\]]+)\]'
        citations = []
        for match in re.finditer(citation_pattern, explanation):
            citations.append({
                "field": match.group(1),
                "value": match.group(2),
                "position": match.start()
            })

        return {
            "explanation": explanation,
            "citations": citations,
            "generated_at": datetime.now().isoformat(),
            "model": settings.LLM_MODEL,
        }

    except Exception as e:
        logger.error(f"LLM explanation generation failed for {county_name}: {e}")

        # Fallback to template-based explanation
        return generate_fallback_explanation(
            county_name, current_phase, current_vci3m, current_spi,
            crossing_date, crossing_phase, days_to_crossing, confidence,
            priority_score, detail_level, livelihood_zone, seasonal_outlook
        )


async def generate_backtest_analysis(summary: dict) -> dict:
    """
    AI pattern analysis over the statistical backtest results.
    Does NOT generate forecasts — only interprets already-computed hit/miss data.
    """
    context = {
        "total_predictions": summary.get("total_predictions"),
        "correct_predictions": summary.get("correct_predictions"),
        "hit_rate": summary.get("hit_rate"),
        "false_alarm_rate": summary.get("false_alarm_rate"),
        "counties": summary.get("counties", []),
    }

    user_prompt = f"""Analyze this backtest data and identify patterns in where the AR(2) model performs well or poorly:

{json.dumps(context, indent=2)}

Write up what you find. Include [ref:] citations for every specific number mentioned."""

    try:
        messages = [
            {"role": "system", "content": BACKTEST_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        analysis = await call_groq_api(messages, max_tokens=600)

        citation_pattern = r'\[ref:(\w+)=([^\]]+)\]'
        citations = [
            {"field": m.group(1), "value": m.group(2), "position": m.start()}
            for m in re.finditer(citation_pattern, analysis)
        ]

        return {
            "explanation": analysis,
            "citations": citations,
            "generated_at": datetime.now().isoformat(),
            "model": settings.LLM_MODEL,
        }
    except Exception as e:
        logger.error(f"Backtest analysis LLM call failed: {e}")
        n = context["total_predictions"] or 0
        return {
            "explanation": (
                f"Backtest evaluated [ref:total_predictions={n}] county-months. "
                f"Overall hit rate: [ref:hit_rate={summary.get('hit_rate', 0)}]. "
                f"Sample size is currently too small for a reliable pattern analysis — "
                f"more historical bulletin data is needed per county."
            ),
            "citations": [{"field": "total_predictions", "value": str(n)}],
            "generated_at": datetime.now().isoformat(),
            "model": "template-fallback",
        }


async def generate_regional_synthesis(queue_items: list[dict]) -> dict:
    """
    Cross-county pattern synthesis over the current priority queue.
    Reasons over already-computed phase/region/livelihood data — does not forecast.
    """
    context = [
        {
            "county": item.get("county_name"),
            "region": item.get("region"),
            "livelihood_zone": item.get("livelihood_zone"),
            "phase": item.get("current_phase"),
            "days_to_crossing": item.get("days_to_crossing"),
        }
        for item in queue_items
    ]

    user_prompt = f"""Current county statuses:

{json.dumps(context, indent=2)}

Identify any regional or livelihood-zone clustering among counties in Alert, Alarm, or Emergency phase. Cite each county referenced."""

    try:
        messages = [
            {"role": "system", "content": REGIONAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        analysis = await call_groq_api(messages, max_tokens=400)

        citation_pattern = r'\[ref:(\w+)=([^\]]+)\]'
        citations = [
            {"field": m.group(1), "value": m.group(2), "position": m.start()}
            for m in re.finditer(citation_pattern, analysis)
        ]
        return {
            "synthesis": analysis,
            "citations": citations,
            "generated_at": datetime.now().isoformat(),
            "model": settings.LLM_MODEL,
        }
    except Exception as e:
        logger.error(f"Regional synthesis LLM call failed: {e}")
        elevated = [c for c in context if c["phase"] not in (None, "Normal")]
        return {
            "synthesis": f"{len(elevated)} counties currently outside Normal phase. Regional synthesis unavailable — retry shortly.",
            "citations": [],
            "generated_at": datetime.now().isoformat(),
            "model": "template-fallback",
        }


def generate_fallback_explanation(
    county_name: str,
    current_phase: str,
    current_vci3m: Optional[float],
    current_spi: Optional[float],
    crossing_date: Optional[str],
    crossing_phase: Optional[str],
    days_to_crossing: Optional[int],
    confidence: Optional[float],
    priority_score: float,
    detail_level: str = "summary",
    livelihood_zone: Optional[str] = None,
    seasonal_outlook: Optional[dict] = None
) -> dict:
    """
    Template-based fallback when the LLM API is unavailable.
    Still includes proper citations.
    """
    citations = []
    parts = []

    vci_str = f"[ref:VCI3M={current_vci3m}]" if current_vci3m else ""
    spi_str = f"[ref:SPI={current_spi}]" if current_spi else ""

    if current_vci3m:
        citations.append({"field": "VCI3M", "value": str(current_vci3m)})
    if current_spi:
        citations.append({"field": "SPI", "value": str(current_spi)})

    if detail_level == "summary":
        if crossing_date and days_to_crossing:
            conf_pct = f"{confidence*100:.0f}" if confidence else "N/A"
            parts.append(
                f"{county_name} is currently in [ref:phase={current_phase}] phase "
                f"with VCI3M at {vci_str}, projected to cross into "
                f"[ref:crossing_phase={crossing_phase}] around [ref:crossing={crossing_date}] "
                f"({days_to_crossing} days) at [ref:confidence={conf_pct}%] confidence."
            )
            citations.extend([
                {"field": "phase", "value": current_phase},
                {"field": "crossing_phase", "value": crossing_phase},
                {"field": "crossing", "value": crossing_date},
                {"field": "confidence", "value": f"{conf_pct}%"},
            ])
        else:
            parts.append(
                f"{county_name} is in [ref:phase={current_phase}] phase "
                f"with VCI3M at {vci_str}. No threshold crossing projected "
                f"within the forecast window."
            )
            citations.append({"field": "phase", "value": current_phase})
    else:
        parts.append(
            f"**Current Situation:** {county_name} county is currently classified "
            f"in the [ref:phase={current_phase}] phase of NDMA's drought classification system. "
            f"The 3-month Vegetation Condition Index (VCI3M) stands at {vci_str}"
            + (f", with a Standardized Precipitation Index (SPI) of {spi_str}" if current_spi else "")
            + "."
        )
        citations.append({"field": "phase", "value": current_phase})

        if crossing_date and days_to_crossing:
            conf_pct = f"{confidence*100:.0f}" if confidence else "N/A"
            parts.append(
                f"\n\n**Forecast:** Based on the autoregressive projection of VCI3M trends, "
                f"{county_name} is projected to cross into [ref:crossing_phase={crossing_phase}] "
                f"phase around [ref:crossing={crossing_date}] — approximately {days_to_crossing} days "
                f"from now. This forecast carries a [ref:confidence={conf_pct}%] confidence level. "
                f"The confidence interval widens with the forecast horizon, reflecting the inherent "
                f"uncertainty in projecting vegetation conditions."
            )
            citations.extend([
                {"field": "crossing_phase", "value": crossing_phase},
                {"field": "crossing", "value": crossing_date},
                {"field": "confidence", "value": f"{conf_pct}%"},
            ])

            parts.append(
                f"\n\n**Recommended Action:** Given the projected transition to "
                f"{crossing_phase} within {days_to_crossing} days, consider activating "
                f"early preparedness measures. This may include alerting County Steering Group "
                f"members, reviewing water trucking capacity, and monitoring the next NDMA "
                f"bulletin closely for confirmation of this trend."
            )
        else:
            parts.append(
                f"\n\n**Forecast:** The VCI3M projection does not indicate a threshold "
                f"crossing within the 6-week forecast window. Conditions are expected to "
                f"remain within the current phase classification."
            )
            parts.append(
                f"\n\n**Recommended Action:** Continue routine monitoring. No immediate "
                f"escalation appears necessary based on current projections."
            )

        if seasonal_outlook:
            period = seasonal_outlook.get("period", "the current season")
            outlook_text = seasonal_outlook.get("rainfall_outlook", "")
            parts.append(
                f"\n\n**Regional Context:** ICPAC's seasonal rainfall outlook for "
                f"[ref:seasonal_outlook={period}] reports: {outlook_text} Weigh this regional "
                f"signal against the county-level forecast above before treating it as confirmed."
            )
            citations.append({"field": "seasonal_outlook", "value": period})

        if livelihood_zone:
            zone_note = {
                "pastoralist": (
                    "Pastoralist zone — prioritize early livestock vaccination, grazing "
                    "corridor management, and water trucking readiness ahead of any phase shift."
                ),
                "agro-pastoralist": (
                    "Agro-pastoralist zone — focus on crop residue preservation, soil moisture "
                    "conservation, and food stock monitoring alongside livestock condition."
                ),
                "mixed": (
                    "Mixed livelihood zone — monitor both settled farming output and local "
                    "market food stock levels, since neither livestock nor crops alone drive this county's outcomes."
                ),
            }.get(
                livelihood_zone,
                "Monitor local livelihood indicators alongside this forecast.",
            )
            parts.append(f"\n\n**Livelihood Guidance ({livelihood_zone}):** {zone_note}")

    return {
        "explanation": "".join(parts),
        "citations": citations,
        "generated_at": datetime.now().isoformat(),
        "model": "template-fallback",
    }


async def generate_batch_summaries(
    counties_data: list[dict],
    seasonal_outlook: Optional[dict] = None
) -> dict[int, str]:
    """
    Generate summary explanations for multiple counties (for the priority queue).

    `seasonal_outlook` is fetched once by the caller and shared across every
    county in the batch — it's a regional signal, not county-specific.
    """
    summaries = {}

    for county in counties_data:
        try:
            result = await generate_explanation(
                county_name=county.get("county_name", "Unknown"),
                current_phase=county.get("current_phase", "Normal"),
                current_vci3m=county.get("current_vci3m"),
                current_spi=county.get("current_spi"),
                forecast_values=county.get("forecast_values", []),
                crossing_date=county.get("crossing_date"),
                crossing_phase=county.get("crossing_phase"),
                days_to_crossing=county.get("days_to_crossing"),
                confidence=county.get("confidence"),
                priority_score=county.get("priority_score", 0),
                livelihood_zone=county.get("livelihood_zone"),
                seasonal_outlook=seasonal_outlook,
                detail_level="summary"
            )
            summaries[county["county_id"]] = result["explanation"]
        except Exception as e:
            logger.error(f"Failed to generate summary for county {county.get('county_name')}: {e}")
            summaries[county["county_id"]] = f"{county.get('county_name', 'Unknown')} — forecast unavailable."

    return summaries
