# Pulsecast — Product & Design Spec

## Problem

NDMA already collects the data and defines the phase system — but it's a *monitoring* system, not a forecasting one. It shows coordinators what's happening now, not what's coming. Every user currently does the same manual work every month: read a dense PDF bulletin, translate the technical indicators, judge which counties need attention first, then decide what to do — with no lead time to act before a phase change is already official, and no easy way to see several counties drifting toward the same crisis at once.

## Solution

Pulsecast takes NDMA's own published data, phases, and thresholds and projects them forward — using a peer-reviewed, NDMA-co-developed forecasting method — so a coordinator sees not just where a county stands today, but when it's likely to cross into a worse phase, weeks before the next bulletin confirms it. It compresses "read → translate → judge → decide" into "open dashboard → see a ranked, explained, sourced forecast → act," with every number traceable back to its source so it holds up as real evidence, not an AI guess.

---

## Features — what and why

### Data ingestion
- **Bulletin fetcher** — pulls NDMA's monthly PDFs automatically. Manual pulling defeats the point.
- **PDF parser** — extracts per-county phase + VCI3M/SPI values. Everything downstream depends on this being reliable.
- **Historical backfill** — reconstructs a multi-month series per county. Needed for the model to learn from, and for the backtest to check against.
- **Structured storage** — normalizes messy PDF output into clean `{county, month, VCI3M, SPI, phase}` records.

### Forecasting engine
- **Per-county AR model** — the actual "weeks in advance" claim. Without it this is just a nicer viewer for data NDMA already publishes.
- **4–6 week VCI3M projection** — matches the lead time the underlying research shows is actually useful for preparedness action.
- **Threshold-crossing detector** — turns a raw forecast number into the question a coordinator actually asks: *is this about to get worse, and when.*

### Priority & classification
- **Mapping onto NDMA's real 5-phase system** — using government categories instead of an invented score is what makes this usable in an actual CSG meeting, not just a demo.
- **Priority score** (severity × time-to-crossing × confidence) — turns dozens of individual forecasts into one ranked list, which is the actual product for someone with limited time.
- **Ranked, sortable queue** — the primary interaction: top-down urgency scanning, not county-by-county lookup.

### AI translation layer
- **Plain-language explanation** — replaces the manual "translate the bulletin" step — the actual bottleneck this exists to remove.
- **Grounding/citation to source values** — every generated sentence traceable to a real number. This is the line between a decision-support tool and an LLM confidently making things up about a humanitarian topic. Non-negotiable, not a nice-to-have.

### Validation / trust layer
- **Backtest panel** — forecast vs. what NDMA's later bulletins actually confirmed. This is what earns trust from someone who has no reason to believe a new tool over their own read of the bulletin.
- **Confidence per forecast** — monthly-cadence data will be noisier than the dense satellite data the original research used. Showing uncertainty honestly protects credibility more than a clean-looking number would.

### Depth features
- **Livelihood-specific guidance** (pastoralist vs. agro-pastoralist) — same forecast, different implied action depending on how people use the land. This is where "actionable" stops being a buzzword.
- **Sensitivity note** ("what would change this") — turns a static forecast into something a coordinator can reason with, not just read.
- **Swahili output** — the people implementing the response aren't only the English-reading coordinator.
- **Choropleth map** — fastest way to see neighboring counties drifting toward the same phase at once, which a list view hides.
- **Shareable summary / export** — a coordinator's real next move is putting this in front of other people (a CSG meeting, a field-team message). One button that copies a clean, sourced summary is cheap and closes that loop.

---

## Visual direction

This is a field instrument for a serious decision, not a SaaS dashboard — closer to a met-office chart or a survey sheet than a startup product. Explicitly avoiding the two reflexive AI-dashboard looks: warm-cream-and-serif-with-terracotta, and near-black-with-one-neon-accent.

**Color** — a cool, slightly desaturated "field paper" base, not warm cream:
- `bg` `#EDEEE8` · `surface` `#F6F6F2` · `ink` `#232A2E` · `ink-muted` `#5B6560`

Then the real signature: instead of one brand accent, use NDMA's actual 5-phase system as a functional sequential ramp — it's structural information, not decoration, so it does double duty as badges, chart lines, map shading, and queue borders:
- Normal `#7A9B76` (moss) → Alert `#C9A24B` (ochre) → Alarm `#B9713A` (rust) → Emergency `#9B3B34` (brick, not neon-alarm red) → Recovery `#4A8B8C` (cool teal — deliberately a different hue family than Normal, so "recovering" reads as its own trajectory, not just "back to green")

**Type** — a condensed technical grotesk for display/headings (reads like instrumentation, not editorial content); a clean humanist sans for body (Inter / IBM Plex Sans); and — this one matters functionally, not just aesthetically — a **monospace with tabular figures for every data value** (VCI3M numbers, dates). Numbers scanned down a column need to align; that's the only typeface choice that reliably does it.

**Layout** — not a card grid. Priority queue is a single ranked column (the rank number is real information here, unlike decorative 01/02/03 — keep it). County detail is a two-pane split, chart-left/explanation-right (stacked on mobile). Evidence trail is a plain, dense table — deliberately *less* designed than the rest of the app, since looking like a data printout is what makes it read as evidence rather than more app chrome.

**Signature element** — the threshold-crossing line. Every chart, from a tiny sparkline in the queue to the full chart on county detail, shows the forecast line visibly approaching and crossing a labeled threshold tick, with the crossing date called out directly on the line. One visual idea, repeated at every scale, referenced in the AI text and the demo video — it's the product's core insight made visible, not a motif bolted on.

**Quality floor**: responsive to mobile (this will genuinely be opened on phones in the field), visible keyboard focus, and `prefers-reduced-motion` respected given how much of the motion plan below relies on animation.

---

## Pages

**1. Priority Queue (home)** — the front door, and the actual product. Single ranked column, top to bottom by priority score. Top 1–3 entries (soonest crossing) set apart by scale or a thin rule, not shouting color — restraint reads as more trustworthy than alarm-red boxes here. Each row: county name, phase badge, a small threshold-line sparkline, days-to-crossing, one-line AI summary. Sort/filter by phase, region, livelihood zone.

**2. County Detail** — the decision-making screen. Threshold-crossing signature front and center: historical VCI3M solid, forecast continuing lighter/dashed, threshold as a labeled tick, crossing date annotated right on the line. AI explanation beside/below with small reference markers back to the exact source value (click reveals the source row inline, no navigation away). Confidence shown plainly next to the forecast, not tucked in a tooltip.

**3. Evidence Trail** — the credibility screen. Dense table, monospace numerals, one row per parsed bulletin value, each linking to the specific page of the source PDF. The one place where "boring and precise" is the correct choice.

**4. Backtest / Track Record** — proof the forecast has a real history, addressing the overclaiming risk *inside the product*, not just the demo voiceover. Simple predicted-vs-confirmed timeline per county, or an aggregate hit-rate/false-alarm summary. Slightly more muted, technical styling than the rest of the app — it should look like a methods section, because that's what it is.

**5. Regional Map** — surfaces clustering a list hides; the one thing the disaster-response use case specifically needs. Counties shaded by the same severity ramp, click-through to detail. A simple topoJSON Kenya-counties layer is enough — don't over-invest in a GIS stack for this.

**6. About/Methodology** — short, always one tap away, not buried. Bakes "proof-of-concept, not a claim to reproduce the original study's exact accuracy" into the product itself. Probably the highest credibility-per-minute-of-build-time page on this list.

Skip real auth/accounts — not what's being judged, pure time cost for a hackathon build.

---

## Motion design

Every animation should carry information, not decorate — the register is a calibrated instrument, not a consumer app.

- Numbers **tween/count** rather than snap when a forecast loads — reinforces that you're watching a value move toward a threshold.
- Threshold lines **draw left-to-right** on load instead of appearing instantly — the reveal makes the crossing feel like a finding, not chart furniture.
- Priority queue rows **animate position** when re-sorted, so it's trackable which county moved and why, instead of the list just cutting to a new order.
- Urgency on top entries: a slow, subtle pulse **at most** — never blinking or siren-red. Understated urgency reads as more credible than alarm UI for a tool like this.
- Page transitions fast and minimal — a 150–200ms fade is enough. Someone using this in a meeting needs speed, not flourish.
- For the demo video specifically: let the AI explanation visibly **type in the first time**, once — a well-worn but effective way to show the reasoning on camera. Cache it and make every later view instant; don't make real usage wait on a typing effect.

---

## Suggested build order

Ingestion + parser (de-risk this first, it's the single dependency everything else has) → forecasting engine → priority queue UI → county detail → AI translation layer → evidence trail → backtest panel → map / depth features, roughly in that order of value-per-hour.

