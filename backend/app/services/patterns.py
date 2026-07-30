"""
Cross-County Pattern & Anomaly Detection

The AR(2) forecaster in forecast.py only ever looks at a county's last
2 VCI3M readings, so it is structurally blind to two kinds of signal that
live in the data but never reach a 2-point regression window:

  1. Recurrence patterns — a county that has previously entered Alert-or-worse
     in this same calendar month in prior years, or that has sat in
     Alert-or-worse for several consecutive available bulletins without a
     new "crossing" (so the AR trend looks flat, not urgent).

  2. Regional clusters — multiple counties in the same region simultaneously
     in Alert-or-worse phase, which is a materially different risk profile
     (shared rainfall system, cross-border livestock movement, etc.) than
     any single county's forecast captures alone.

Both detectors here are deterministic and evidence-cited (they name the
exact months/counties behind every flag) rather than an LLM asked to
"notice" a pattern in a JSON dump — see historical comparison in
llm.py's generate_regional_synthesis, which is now grounded on
`detect_regional_clusters` output instead of eyeballing raw records.

Everything here operates only on real, published NDMA phase classifications
(never on the VCI3M proxy values used to backfill pre-live months — see
historical_seed.py's docstring on why phase is the trustworthy field for
those months and VCI3M is not).
"""

from collections import defaultdict
from typing import Optional

from app.services.parser import get_phase_severity

# Below Alert severity, a phase isn't "concerning" for pattern purposes.
CONCERNING_SEVERITY = get_phase_severity("Alert")

# Minimum consecutive available bulletins (not necessarily consecutive
# calendar months — NDMA's live site only ever exposes the current month,
# so real gaps exist between the historical backfill and live records) all
# showing Alert-or-worse before it counts as a persistent/chronic pattern.
PERSISTENT_STREAK_LENGTH = 3

# A region needs at least this many ASAL counties tracked before a
# "cluster" is a meaningful concept rather than a coincidence.
MIN_REGION_SIZE_FOR_CLUSTER = 3
MIN_CLUSTER_COUNT = 3
MIN_CLUSTER_FRACTION = 0.5


def _month_number(month: str) -> int:
    return int(month.split("-")[1])


def _year(month: str) -> str:
    return month.split("-")[0]


def detect_recurrence_pattern(county_name: str, history: list[dict]) -> Optional[dict]:
    """
    Detect per-county temporal patterns the AR(2) model's 2-point window
    can't see: same-month-in-a-prior-year recurrence, and persistent
    multi-bulletin severity streaks.

    Args:
        county_name: for the human-readable note.
        history: this county's bulletins, chronological ascending, each
            {"month": "YYYY-MM", "phase": str}.

    Returns None if no pattern qualifies, otherwise a dict:
        {
          "type": "recurrence",
          "same_month_years": [...],        # prior years this exact
                                             # calendar month also hit
                                             # Alert-or-worse (may be empty)
          "same_month_occurrences": [...],  # {month, phase} evidence
          "persistent_streak": int | None,  # length of current
                                             # Alert-or-worse streak, if any
          "streak_occurrences": [...],      # {month, phase} evidence
          "note": "<human-readable summary>",
        }
    """
    if not history:
        return None

    latest = history[-1]
    current_month_num = _month_number(latest["month"])
    current_year = _year(latest["month"])

    # --- Same calendar month, different year ---
    same_month_hits = [
        row for row in history[:-1]
        if _month_number(row["month"]) == current_month_num
        and _year(row["month"]) != current_year
        and get_phase_severity(row["phase"]) >= CONCERNING_SEVERITY
    ]
    same_month_years = sorted({_year(r["month"]) for r in same_month_hits})

    # --- Persistent streak ending at the latest bulletin ---
    streak_occurrences: list[dict] = []
    if get_phase_severity(latest["phase"]) >= CONCERNING_SEVERITY:
        for row in reversed(history):
            if get_phase_severity(row["phase"]) >= CONCERNING_SEVERITY:
                streak_occurrences.insert(0, row)
            else:
                break
    streak_len = len(streak_occurrences)
    has_streak = streak_len >= PERSISTENT_STREAK_LENGTH

    if not same_month_years and not has_streak:
        return None

    note_parts = []
    if same_month_years:
        year_word = "years" if len(same_month_years) > 1 else "year"
        note_parts.append(
            f"{county_name} previously reached {'/'.join(sorted({r['phase'] for r in same_month_hits}))} "
            f"phase in this same calendar month in {len(same_month_years)} prior {year_word} "
            f"({', '.join(same_month_years)})."
        )
    if has_streak:
        note_parts.append(
            f"{county_name} has been at {latest['phase']} phase or worse for "
            f"{streak_len} consecutive recorded bulletins "
            f"({streak_occurrences[0]['month']} \u2192 {streak_occurrences[-1]['month']}), "
            f"a chronic pattern a 2-point trend line won't flag as a new event."
        )

    return {
        "type": "recurrence",
        "same_month_years": same_month_years,
        "same_month_occurrences": same_month_hits,
        "persistent_streak": streak_len if has_streak else None,
        "streak_occurrences": streak_occurrences if has_streak else [],
        "note": " ".join(note_parts),
    }


def detect_regional_clusters(latest_by_county: list[dict]) -> dict[int, dict]:
    """
    Detect regions where multiple counties are simultaneously at
    Alert-or-worse in their most recent bulletin.

    Args:
        latest_by_county: one row per county's latest bulletin:
            {"county_id", "county_name", "region", "phase"}.

    Returns:
        {county_id: cluster_dict} — only for counties that are both
        at-risk themselves AND part of a qualifying regional cluster.
        cluster_dict = {
          "type": "regional_cluster",
          "region": str,
          "at_risk_count": int,
          "region_size": int,
          "peer_counties": [names other than this one],
          "note": "<human-readable summary>",
        }
    """
    by_region: dict[str, list[dict]] = defaultdict(list)
    for row in latest_by_county:
        if row.get("region"):
            by_region[row["region"]].append(row)

    result: dict[int, dict] = {}

    for region, rows in by_region.items():
        if len(rows) < MIN_REGION_SIZE_FOR_CLUSTER:
            continue

        at_risk = [r for r in rows if get_phase_severity(r.get("phase")) >= CONCERNING_SEVERITY]
        if len(at_risk) < MIN_CLUSTER_COUNT:
            continue
        if len(at_risk) / len(rows) < MIN_CLUSTER_FRACTION:
            continue

        at_risk_names = sorted(r["county_name"] for r in at_risk)
        for row in at_risk:
            peers = [n for n in at_risk_names if n != row["county_name"]]
            result[row["county_id"]] = {
                "type": "regional_cluster",
                "region": region,
                "at_risk_count": len(at_risk),
                "region_size": len(rows),
                "peer_counties": peers,
                "note": (
                    f"{len(at_risk)} of {len(rows)} tracked {region} counties are simultaneously "
                    f"at Alert phase or worse ({', '.join(at_risk_names)}) — a shared regional "
                    f"drought cluster, not an isolated county event."
                ),
            }

    return result


def combine_pattern_signals(
    recurrence: Optional[dict],
    cluster: Optional[dict],
) -> Optional[dict]:
    """Merge a county's recurrence + cluster signals into one payload for
    storage/API, or None if neither detector fired."""
    if not recurrence and not cluster:
        return None
    signals = []
    if recurrence:
        signals.append(recurrence)
    if cluster:
        signals.append(cluster)
    return {"signals": signals}


def pattern_score_boost(pattern_signals: Optional[dict]) -> float:
    """
    Priority-score points to add on top of the base AR(2)-driven score.

    Kept additive and modest relative to calculate_priority_score's 0-100
    scale — these are meant to surface patterns the AR(2) trend missed,
    not to dominate over an already-urgent AR(2) crossing.
    """
    if not pattern_signals:
        return 0.0

    boost = 0.0
    for signal in pattern_signals.get("signals", []):
        if signal["type"] == "recurrence":
            if signal.get("same_month_years"):
                # Stronger with more independent years of evidence.
                boost += 8.0 + 4.0 * min(2, len(signal["same_month_years"]) - 1)
            if signal.get("persistent_streak"):
                boost += 10.0
        elif signal["type"] == "regional_cluster":
            boost += 12.0

    return boost
