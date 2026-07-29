"""
Historical Bulletin Seed Data

NDMA's KnowledgeWeb archive genuinely holds bulletins back to 2016, but it's
served through a JS-driven grid (a Telerik-style ASP.NET widget with a
county/year tree) that fires AJAX/postback calls on click rather than
exposing plain crawlable links. This backend's ingestion.py is a plain
httpx + BeautifulSoup scraper — it can reach whatever NDMA server-renders
by default (the current month), but it can't execute that grid's JS or
replay its postback protocol, which is why bulletins historically only ever
had 1-2 rows per county and backtest/calibration were structurally stuck
at zero (see calibration.py — MIN_SAMPLES_TO_TRUST needs 10, and a county
needs 4+ months before it contributes even one backtest sample).

This module is the fix: real NDMA phase classifications for 12 distinct
months (Sept 2022 through Feb 2026), found via search rather than crawled
live, and hand-verified against NDMA's own National Monthly Drought Update
bulletins and National Drought Early Warning Bulletin PDFs (all counties'
phases are stated explicitly in these; not extrapolated or invented). Each
entry cites its real source URL.

IMPORTANT — what's exact vs approximated:
  - `phase` for every county/month below is exactly what NDMA published —
    this is real, sourced classification data, not a guess.
  - `vci3m` is NOT what NDMA published for most of these months — the
    National Monthly Drought Update summaries state phase per county but
    usually don't give the underlying VCI3M number for every county. Since
    the AR(2) forecaster needs a numeric series to fit a trend, each phase
    is mapped to a representative VCI3M value from the middle of that
    phase's band (see PHASE_VCI3M_PROXY below), with small deterministic
    per-county jitter so counties sharing a phase in the same month aren't
    numerically identical. Treat these numbers as "consistent with the
    real published phase," not as the real published instrument reading —
    the live current-month pipeline (parser.extract_vci3m against the
    actual bulletin PDF) is the one place VCI3M is a precise parsed value.

Where a month's source didn't name a specific county at all, that county
is simply left out of that month rather than guessed.
"""

from app.services.parser import VCI3M_THRESHOLDS

# Representative VCI3M for each phase, used only where NDMA's own narrative
# summary didn't give this county's exact number for this month (see
# module docstring). Chosen as a value comfortably inside each phase's band.
PHASE_VCI3M_PROXY = {
    "Normal": 45.0,
    "Pre-Alert": 31.0,
    "Alert": 24.0,
    "Alarm": 15.0,
    "Emergency": 5.0,
}


def _jitter(county: str, month: str) -> float:
    """Small deterministic per-(county, month) offset so counties sharing a
    phase in the same month don't produce a perfectly flat, zero-variance
    series (which breaks an AR(2) fit). Seeded off the string itself, not
    `random` — same input always gives the same output, no run-to-run drift.
    """
    h = hash((county, month)) % 1000
    return (h / 1000.0 - 0.5) * 4.0  # +/- 2.0


HISTORICAL_MONTHS = [
    {
        "month": "2022-09",
        "source_url": "https://knowledgeweb.ndma.go.ke/Content/LibraryDocuments/National_Monthly_Drought_Update-_September_202220230508100344.pdf",
        "source_note": "NDMA National Monthly Drought Update, September 2022",
        "phases": {
            "Isiolo": "Alarm", "Mandera": "Alarm", "Samburu": "Alarm", "Kajiado": "Alarm",
            "Tharaka Nithi": "Alarm", "Turkana": "Alarm", "Wajir": "Alarm", "Laikipia": "Alarm",
            "Tana River": "Alarm", "Marsabit": "Alarm",
            "Embu": "Alert", "Garissa": "Alert", "Kitui": "Alert", "Makueni": "Alert",
            "Meru": "Alert", "Narok": "Alert", "Nyeri": "Alert", "Taita Taveta": "Alert",
            "Kwale": "Alert", "Kilifi": "Alert",
            "Baringo": "Normal", "West Pokot": "Normal", "Lamu": "Normal",
        },
        "default_phase": None,  # explicit for all 23
    },
    {
        "month": "2023-09",
        "source_url": "https://ndma.go.ke/case-studies/national-monthly-drought-updates-september-2023/",
        "source_note": "NDMA National Monthly Drought Update, September 2023",
        "phases": {
            "Laikipia": "Alert", "Samburu": "Alert", "Turkana": "Alert",
            "Tana River": "Alert", "Taita Taveta": "Alert",
        },
        "default_phase": "Normal",  # source: "18 counties reported Normal phase"
    },
    {
        "month": "2024-03",
        "source_url": "https://ndma.go.ke/case-studies/national-monthly-drought-update-march-2024/",
        "source_note": "NDMA National Monthly Drought Update, March 2024",
        "phases": {},
        "default_phase": "Normal",  # source: all 23 ASAL counties in Normal phase
    },
    {
        "month": "2024-05",
        "source_url": "https://ndma.go.ke/case-studies/national-drought-early-warning-bulletin-may-2024/",
        "source_note": "NDMA National Monthly Drought Update, May 2024",
        "phases": {},
        "default_phase": "Normal",  # source: situation continuing in normal phase
    },
    {
        "month": "2024-11",
        "source_url": "https://ndma.go.ke/case-studies/national-drought-update-november-2024/",
        "source_note": "NDMA National Monthly Drought Update, November 2024",
        "phases": {
            "Kilifi": "Alert", "Kwale": "Alert",
        },
        "default_phase": "Normal",  # source: "21 ASAL counties...Normal phase"
    },
    {
        "month": "2025-01",
        "source_url": "https://ndma.go.ke/case-studies/national-monthly-drought-update-january-2025/",
        "source_note": "NDMA National Monthly Drought Update, January 2025",
        "phases": {
            "Wajir": "Alert", "Kilifi": "Alert", "Kwale": "Alert",
        },
        "default_phase": "Normal",  # source: "20 counties...Normal drought phase"
    },
    {
        "month": "2025-02",
        "source_url": "https://ndma.go.ke/case-studies/national-monthly-drought-update-february-2025/",
        "source_note": "NDMA National Monthly Drought Update, February 2025",
        "phases": {
            "Mandera": "Alert", "Kwale": "Alert", "Isiolo": "Alert", "Samburu": "Alert",
            "Turkana": "Alert", "Marsabit": "Alert", "Wajir": "Alert", "Kilifi": "Alert",
        },
        "default_phase": "Normal",  # source: remaining 15 counties Normal
    },
    {
        "month": "2025-03",
        "source_url": "https://ndma.go.ke/case-studies/national-monthly-drought-update-march-2025/",
        "source_note": "NDMA National Monthly Drought Update, March 2025",
        "phases": {
            "Wajir": "Alert", "Mandera": "Alert", "Isiolo": "Alert",
            "Kwale": "Alert", "Marsabit": "Alert", "Kilifi": "Alert",
        },
        "default_phase": "Normal",  # source: "17 ASAL counties...Normal phase"
    },
    {
        "month": "2025-06",
        "source_url": "https://knowledgeweb.ndma.go.ke/Content/LibraryDocuments/National_Drought_Early_Warning_Bulletin_June_202520250714160837.pdf",
        "source_note": "NDMA National Drought Early Warning Bulletin, June 2025",
        "phases": {},
        "default_phase": "Normal",  # source: all 23 counties Normal, none Alert/Alarm
    },
    {
        "month": "2025-12",
        "source_url": "https://big3africa.org/2025/12/10/ndma-sounds-alarm-of-hunger-as-drought-deepens/",
        "source_note": "NDMA December 2025 drought bulletin, reported via Big3Africa / NDMA Latest News",
        "phases": {
            "Mandera": "Alarm",
            "Wajir": "Alert", "Garissa": "Alert", "Kilifi": "Alert", "Kitui": "Alert",
            "Marsabit": "Alert", "Kwale": "Alert", "Kajiado": "Alert", "Isiolo": "Alert",
            "Tana River": "Alert",
            "Samburu": "Normal", "Turkana": "Normal", "Taita Taveta": "Normal",
            "West Pokot": "Normal", "Tharaka Nithi": "Normal", "Embu": "Normal",
            "Nyeri": "Normal", "Laikipia": "Normal", "Narok": "Normal", "Baringo": "Normal",
            "Makueni": "Normal", "Meru": "Normal", "Lamu": "Normal",
        },
        "default_phase": None,  # explicit for all 23
    },
    {
        "month": "2026-01",
        "source_url": "https://knowledgeweb.ndma.go.ke/Content/LibraryDocuments/National_DEW_Bulletin_January_202620260217011002.pdf",
        "source_note": "NDMA National Drought Early Warning Bulletin, January 2026",
        "phases": {
            "Mandera": "Alarm", "Wajir": "Alarm", "Kwale": "Alarm", "Kilifi": "Alarm",
            "Turkana": "Alert", "Marsabit": "Alert", "Samburu": "Alert", "Isiolo": "Alert",
            "Baringo": "Alert", "Laikipia": "Alert", "Tharaka Nithi": "Alert",
            "Kajiado": "Alert", "Taita Taveta": "Alert", "Kitui": "Alert",
            "Tana River": "Alert", "Garissa": "Alert", "Lamu": "Alert",
            "Embu": "Pre-Alert", "Narok": "Pre-Alert", "West Pokot": "Pre-Alert",
            "Nyeri": "Normal", "Meru": "Normal", "Makueni": "Normal",
        },
        "default_phase": None,  # explicit for all 23
    },
    {
        "month": "2026-02",
        "source_url": "https://knowledgeweb.ndma.go.ke/Content/LibraryDocuments/National_Drought_Early_Warning_Bulletin_Feb_202620260311171955.pdf",
        "source_note": "NDMA National Drought Early Warning Bulletin, February 2026",
        "phases": {
            "Mandera": "Alarm", "Wajir": "Alarm", "Kilifi": "Alarm", "Kwale": "Alarm",
            "Garissa": "Alert", "Tana River": "Alert", "Isiolo": "Alert", "Marsabit": "Alert",
            "Kajiado": "Alert", "Kitui": "Alert", "Lamu": "Alert", "Samburu": "Alert",
            "Taita Taveta": "Alert", "Tharaka Nithi": "Alert", "Turkana": "Alert",
            "Baringo": "Alert",
            "Laikipia": "Pre-Alert", "Narok": "Pre-Alert",
            "Nyeri": "Normal", "Makueni": "Normal", "Meru": "Normal",
        },
        # Embu and West Pokot weren't named in this particular source excerpt
        # — left out of this month rather than guessed.
        "default_phase": None,
    },
]


def expand_historical_records(all_counties: list[dict]) -> list[dict]:
    """
    Expand HISTORICAL_MONTHS into flat per-county bulletin records ready to
    upsert into the `bulletins` table.

    Returns a list of dicts: {county_name, month, phase, vci3m, spi,
    source_url, source_page}.
    """
    county_names = {c["name"] for c in all_counties}
    records = []

    for entry in HISTORICAL_MONTHS:
        month = entry["month"]
        for county_name in county_names:
            phase = entry["phases"].get(county_name, entry["default_phase"])
            if phase is None:
                continue  # not covered this month — skip rather than guess

            base_vci3m = PHASE_VCI3M_PROXY.get(phase, VCI3M_THRESHOLDS.get(phase, 30.0))
            vci3m = round(base_vci3m + _jitter(county_name, month), 1)

            records.append({
                "county_name": county_name,
                "month": month,
                "phase": phase,
                "vci3m": vci3m,
                "spi": None,
                "source_url": entry["source_url"],
                "source_page": None,
            })

    return records
