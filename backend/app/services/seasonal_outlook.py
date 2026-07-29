"""
ICPAC Seasonal Outlook Service

Pulls the current regional seasonal rainfall outlook published by ICPAC —
the IGAD Hackathon's own host organization — as a second, independent
signal alongside the statistical VCI3M forecast. The AI translation layer
uses this to reconcile the two: when they agree, that's stated as
strengthening confidence; when they disagree, the explanation flags it
explicitly instead of silently picking one signal over the other.

This is a best-effort scrape of a public page, not a stable API — ICPAC
doesn't publish one for this product. It fails closed: any fetch or parse
problem returns None, and callers must treat a missing outlook as "no
second signal available this run," not an error. It has not been tested
against the live site from this environment (no network egress to
icpac.net here) — verify the parsing against the real page structure
before relying on it.
"""

import re
import time
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ICPAC_SEASONAL_FORECAST_URL = "https://www.icpac.net/seasonal-forecast/"

# The outlook is published a handful of times per season, not worth
# re-fetching on every request.
_cache: dict = {"data": None, "fetched_at": 0.0}
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 1 day

_MONTH = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
PERIOD_PATTERN = re.compile(rf"\b{_MONTH}\s*[-–]\s*{_MONTH}\s+(\d{{4}})\b")

# Lines under a "Rainfall forecast" heading longer than this are treated as
# outlook prose rather than nav labels or image captions.
_MIN_BULLET_LENGTH = 25
_SECTION_STOP_WORDS = ("download", "facebook", "twitter", "seasonal forecasts", "share")


async def fetch_seasonal_outlook(force_refresh: bool = False) -> Optional[dict]:
    """
    Returns the current IGAD-region seasonal rainfall outlook, e.g.:
        {
            "period": "August - October 2026",
            "rainfall_outlook": "Wetter-than-normal conditions expected over...",
            "temperature_outlook": "Warmer than usual temperatures expected...",
            "source_url": "https://www.icpac.net/seasonal-forecast/",
            "fetched_at": <unix timestamp>,
        }
    Returns None if the page couldn't be fetched or parsed — callers must
    handle that as "no second signal," not surface it as an error.
    """
    now = time.time()
    if not force_refresh and _cache["data"] and (now - _cache["fetched_at"] < _CACHE_TTL_SECONDS):
        return _cache["data"]

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(
                ICPAC_SEASONAL_FORECAST_URL,
                headers={"User-Agent": "Pulsecast/1.0 (IGAD Hackathon 2026 project; drought forecasting)"},
            )

        if response.status_code != 200:
            logger.warning("ICPAC seasonal forecast page returned status %s", response.status_code)
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text("\n")

        period_match = PERIOD_PATTERN.search(text)
        period = period_match.group(0).strip() if period_match else None

        rainfall_outlook = _extract_section(text, "Rainfall forecast")
        temperature_outlook = _extract_section(text, "Temperature forecast")

        if not period or not rainfall_outlook:
            logger.warning(
                "Could not parse ICPAC seasonal outlook — page structure may have changed since this was written"
            )
            return None

        result = {
            "period": period,
            "rainfall_outlook": rainfall_outlook,
            "temperature_outlook": temperature_outlook,
            "source_url": ICPAC_SEASONAL_FORECAST_URL,
            "fetched_at": now,
        }
        _cache["data"] = result
        _cache["fetched_at"] = now
        return result

    except httpx.HTTPError as exc:
        logger.warning("Could not reach ICPAC seasonal forecast page: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — this must never break forecast generation
        logger.error("Error parsing ICPAC seasonal outlook: %s", exc)
        return None


def _extract_section(text: str, heading: str) -> Optional[str]:
    """
    Grabs the prose lines that follow a heading like "Rainfall forecast"
    up to the next stop marker (download link, share buttons, or the
    archive list heading). The live page repeats section labels as both
    nav text and content headings, so this takes the first occurrence
    with substantial content directly beneath it.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for i, line in enumerate(lines):
        if line.lower() != heading.lower():
            continue
        bullets = []
        for follow in lines[i + 1: i + 12]:
            lowered = follow.lower()
            if any(lowered.startswith(stop) or lowered == stop for stop in _SECTION_STOP_WORDS):
                break
            if len(follow) > _MIN_BULLET_LENGTH:
                bullets.append(follow.lstrip("-•* "))
        if bullets:
            return " ".join(bullets)
    return None
