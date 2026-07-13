# Pulsecast — Demo & Product Notes

*This file exists to give context that isn't visible from code alone: who this is for, what it does end-to-end, and what makes it different from existing tools. Intended for anyone (human or AI) generating documentation, demos, or pitch material for this repo.*

---

## One-line summary

Pulsecast is an AI-powered platform that forecasts drought phase transitions in Kenya's counties weeks before they happen, using NDMA's own published data and thresholds — turning a manual, bulletin-reading bottleneck into a ranked, explainable, actionable dashboard.

---

## Features

### Core (MVP)

**Data ingestion**
- Bulletin fetcher — pulls NDMA's monthly county drought bulletin PDFs
- PDF parser — extracts per-county phase classification and underlying VCI/SPI values
- Historical backfill — reconstructs a multi-month time series per county
- Structured storage — normalized `{county, month, VCI3M, SPI, phase}` records

**Forecasting engine**
- Per-county time-series model (autoregressive, following the validated approach in Barrett et al., 2020)
- 4–6 week VCI3M projection
- Threshold-crossing detector — flags *when* a county is likely to cross into a more severe phase, using NDMA's own real thresholds (e.g. VCI3M < 35 for Alert)

**Priority & classification logic**
- Forecasts mapped directly onto NDMA's real 5-phase system (Normal, Alert, Alarm, Emergency, Recovery) — not an invented scoring scheme
- Transparent priority score = severity × time-to-crossing × confidence
- Ranked, sortable county queue

**AI translation layer**
- Converts each forecast into plain-language, cited guidance
- Every generated sentence references the actual indicator values behind it — explainable by design, not a black box

**Dashboard**
- Priority queue view — all counties ranked by urgency
- County detail view — time-series chart with forecast + threshold line, AI explanation, source data table
- Evidence trail — every number links back to the source NDMA bulletin

### Stretch (build if time allows, in this order)
1. Backtest panel — shows how the model's past predictions compare to what actually happened, per NDMA's own later bulletins
2. Confidence intervals on each forecast
3. Livelihood-specific guidance (pastoralist vs. agro-pastoralist framing)
4. Swahili-language output alongside English
5. "What would change this" sensitivity note (e.g. "if rainfall improves 15% next week, this drops to priority 4")
6. Kenya choropleth map view

---

## Who uses this, and how

### County Drought Coordinator (primary user)
**Trigger:** monthly County Steering Group (CSG) meeting, or a routine check between NDMA bulletins.
**Flow:** opens Pulsecast → sees current status *and* forecasted trajectory for their county → if a phase crossing is projected, reads the cited AI explanation of which indicators are driving it → uses that explanation directly in the CSG meeting instead of manually translating the technical bulletin themselves → decides whether early-preparedness actions (water trucking, grazing committee activation) should start now, ahead of the official classification.

### NGO Field Officer (cross-county view)
**Trigger:** deciding where limited resources go this month, across multiple counties.
**Flow:** opens the priority queue → sees which counties need attention first without reading every bulletin individually → clicks into the top-ranked counties to check the evidence trail before committing resources → shares the plain-language explanation with field teams or community leaders as a briefing.

### Disaster Response Team
**Trigger:** regional scan, not tied to a single county.
**Flow:** uses the map/queue view to spot emerging clusters — multiple neighboring counties trending toward the same phase — which isolated, per-county bulletins don't surface well.

### The common thread
All three currently do this manually: read a bulletin, translate it, judge priority, act. Pulsecast compresses that into: open dashboard → see ranked, explained, sourced forecast → act. The value isn't new data — it's cutting the time between information existing and someone deciding what to do about it.

---

## What makes this different from what already exists

**vs. ICPAC's East Africa Hazards Watch** — a comprehensive, well-built multi-hazard monitoring platform, but it reports *current* conditions across many hazard types, built for technical/GIS users. Pulsecast doesn't compete with it or duplicate its data collection — it does one narrow thing Hazards Watch doesn't: forecast *when* a specific, government-recognized phase line will be crossed, ahead of time.

**vs. NDMA's own monthly bulletins** — the actual source of truth, but delivered as dense PDF documents reflecting only current-month conditions. No forecasting, no automatic cross-county prioritization, no plain-language translation — a human currently has to do all of that manually, every month, for every county they're responsible for.

**vs. a generic "AI hazard dashboard"** — Pulsecast isn't summarizing text with an LLM and calling it insight. It operationalizes a specific, peer-reviewed, published-but-never-built research proposal (the "Early Alert" phase suggested by Barrett et al., 2020) using NDMA's real data and real thresholds. The AI layer explains a real quantitative forecast; it isn't the forecast itself.

---

## Demo narrative (for video generation)

**Persona:** a county drought coordinator facing a stack of dense monthly bulletins, trying to figure out which of their counties needs attention first.

**Story arc:** show the manual bottleneck (reading, translating, ranking bulletins by hand) → cut to Pulsecast doing the same job in under a minute → end on the specific early action the lead time enables.

**Screens to prioritize, in this order:**
1. Priority queue (ranked counties, at a glance)
2. County drill-down (forecast chart + threshold line)
3. Evidence trail (source bulletin values, not a black box)
4. AI-generated plain-language explanation

**Framing to include in voiceover — do not skip:**
This is a proof-of-concept built on NDMA's own published bulletin data, demonstrating the operational feasibility of a validated, peer-reviewed forecasting method — not a claim to have reproduced that original study's exact accuracy on this data. Overclaiming here is the single biggest credibility risk with this submission's judges.
