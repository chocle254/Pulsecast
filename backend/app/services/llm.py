"""
LLM Translation Service

Converts quantitative forecasts into plain-language, cited guidance.
Uses Groq's free-tier API (OpenAI-compatible) with llama-3.1-70b
for fast, powerful inference at no cost.

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
6. Never overclaim accuracy — this is a proof-of-concept forecast, not an official NDMA classification
7. Keep it concise — 3-5 sentences maximum for summaries, up to 3 paragraphs for detailed explanations

FORMATTING:
- Use [ref:VCI3M=XX.X] for VCI3M citations
- Use [ref:SPI=X.XX] for SPI citations
- Use [ref:phase=Phase] for phase citations
- Use [ref:crossing=YYYY-MM-DD] for crossing date citations
- Use [ref:confidence=XX%] for confidence citations"""


async def call_groq_api(messages: list[dict], max_tokens: int = 500) -> str:
    """
    Call the Groq API (OpenAI-compatible) for LLM inference.
    Groq offers free-tier access with generous rate limits.
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
    detail_level: str = "summary"
) -> dict:
    """
    Generate a plain-language explanation of a county's forecast.

    Args:
        detail_level: "summary" (1-2 sentences for queue) or "full" (detailed for county page)

    Returns:
        {explanation, citations, generated_at}
    """
    context = {
        "county": county_name,
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
    }

    if detail_level == "summary":
        user_prompt = f"""Generate a ONE-SENTENCE summary for the priority queue for {county_name} county.

Data: {json.dumps(context, indent=2)}

The sentence should convey: current status, what's coming, and urgency. Include [ref:] citations for key values."""
    else:
        user_prompt = f"""Generate a detailed explanation (2-3 paragraphs) for {county_name} county's drought forecast.

Data: {json.dumps(context, indent=2)}

Structure:
1. Current situation — what phase, what the indicators show
2. Forecast — what's projected, when any threshold crossing might happen, confidence level
3. Recommended action — what a coordinator should consider given this forecast

Include [ref:] citations for every specific value mentioned."""

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
            priority_score, detail_level
        )


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
    detail_level: str = "summary"
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

    return {
        "explanation": "".join(parts),
        "citations": citations,
        "generated_at": datetime.now().isoformat(),
        "model": "template-fallback",
    }


async def generate_batch_summaries(counties_data: list[dict]) -> dict[int, str]:
    """
    Generate summary explanations for multiple counties (for the priority queue).
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
                detail_level="summary"
            )
            summaries[county["county_id"]] = result["explanation"]
        except Exception as e:
            logger.error(f"Failed to generate summary for county {county.get('county_name')}: {e}")
            summaries[county["county_id"]] = f"{county.get('county_name', 'Unknown')} — forecast unavailable."

    return summaries
