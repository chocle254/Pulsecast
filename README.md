# Pulsecast

**Drought forecasting and aid-alert broadcasting for Kenya's 23 ASAL counties — built on NDMA's own data.**

Built for the [IGAD Hackathon 2026: Smarter Early Warning, Stronger Communities](https://ndma-hackathon.devpost.com/).

---

## The problem

Kenya's National Drought Management Authority (NDMA) publishes real, government-defined drought bulletins every month — a five-phase system (Normal → Alert → Alarm → Emergency) covering all 23 Arid and Semi-Arid Lands counties. It's a genuinely good monitoring system.

But it's a monitoring system, not a forecasting one — it reports what's already true. Every month, county coordinators and NGO field officers repeat the same manual cycle: read a dense PDF, judge which counties look like they're drifting toward trouble, then decide whether to act — often only after the phase change is already official and the lead time to prepare is gone.

## The solution

Pulsecast takes NDMA's own published bulletins and does two things NDMA's bulletin can't:

1. **Forecasts.** A per-county model projects each county's vegetation-condition trend 4–6 weeks ahead and flags the exact date it's likely to cross into a worse NDMA phase — ranked into one priority queue, explained in plain language, with every claim traceable back to its source bulletin.
2. **Acts.** The moment a county's *confirmed* phase enters Alert, Alarm, or Emergency, a **Send Aid** panel unlocks on that county's page. A coordinator drafts a real distribution — aid type, date, time, drop-off points — and Pulsecast generates a ready-to-broadcast SMS alert in **English and Kiswahili**, sized to real segment limits, with aid type automatically nudged toward livestock feed and water in pastoralist counties.

Pulsecast doesn't just tell someone what's coming. It gives them the message that gets a community ready for it.

---

## Features

### Data ingestion & parsing
- Live scraper pulls NDMA's monthly drought bulletin PDFs directly from NDMA KnowledgeWeb.
- PDF parser extracts per-county VCI3M / SPI values and phase classification.
- Historical backfill (2022–2026) fills gaps the live scraper can't reach, without ever overwriting a live-parsed record.

### Forecasting engine
- Per-county AR(2) model (Yule-Walker / OLS estimation, with a naive-model fallback for sparse counties) projects VCI3M 4–6 weeks ahead.
- Threshold-crossing detector flags the exact date a county is on track to cross into a worse NDMA phase.
- Priority score (severity × time-to-crossing × confidence) collapses 23 individual forecasts into one ranked, actionable queue.
- Forecasts are cross-checked against ICPAC's independent seasonal rainfall outlook rather than trusted alone.

### AI translation layer
- Raw forecast numbers are translated into plain-language explanations.
- Every generated sentence is grounded and citation-linked back to the exact source value — no ungrounded claims about a humanitarian topic.
- Livelihood-aware: pastoralist and agro-pastoralist counties get different guidance than food-only counties.

### Trust & validation
- **Evidence Trail** — every value in the app links back to the specific page of its source PDF.
- **Backtest panel** — past forecasts compared against what NDMA's later bulletins actually confirmed, so the system's track record is visible, not asserted.
- Confidence shown plainly next to every forecast.

### Send Aid — bilingual crisis alert broadcasting
- Gated on NDMA's own phase thresholds: the panel only appears once a county's *current, bulletin-confirmed* phase is Alert, Alarm, or Emergency. There's no path to send a crisis alert for a county that isn't actually in crisis.
- Coordinator enters aid type, date/time, and drop-off locations; Pulsecast composes the outbound SMS text in English **and** Kiswahili, with a live segment counter.
- Aid type defaults to livestock feed & veterinary support in pastoralist livelihood zones, flagged explicitly.
- **Deliberately template-built, not LLM-generated** — a humanitarian broadcast (what aid, where, for whom) is exactly the kind of consequential output that shouldn't come from a model that can hallucinate. Every field in the message is a value the coordinator explicitly entered.
- Hackathon scope: sending is simulated — the exact outbound text is rendered on screen and logged rather than dispatched through a live SMS gateway. Wiring this to a provider like Africa's Talking is the disclosed next step.

### Regional map
- Choropleth map of Kenya's counties shaded by NDMA phase severity, so clustering that a list view hides is visible at a glance.

---

## Tech stack

**Backend** — FastAPI, Uvicorn, pdfplumber (PDF parsing), httpx, BeautifulSoup4 (scraping), aiosqlite/SQLite, statsmodels / NumPy / SciPy / pandas (forecasting), Pydantic.

**Frontend** — Next.js 14, React 18, TypeScript, D3 + topojson-client (map), Tailwind CSS, Framer Motion, lucide-react.

**AI / LLM** — Groq API (Llama-family chat completions) for translation, backtest audit, and regional synthesis, with NVIDIA NIM as a fallback provider. Send Aid alert text is intentionally excluded from this — it's template-assembled, not LLM-generated.

**Data sources** — NDMA County Drought Early Warning Bulletins (live scrape), NDMA historical phase archive (2022–2026, hand-compiled from public bulletins), ICPAC seasonal rainfall outlook.

**Hosting** — Backend on Railway, frontend on Vercel.

All sources and tools above are open-source or publicly documented commercial APIs, used within their published terms.

---

## Architecture

```
NDMA bulletin PDFs (live scrape)
        │
        ▼
  Ingestion + PDF parser  ──►  SQLite (per-county VCI3M/SPI/phase records)
        │
        ▼
  AR(2) forecasting engine  ──►  threshold-crossing detection  ──►  priority score
        │
        ▼
  AI translation layer (Groq / NVIDIA NIM, grounded + cited)
        │
        ▼
  FastAPI (/api/counties, /api/forecast, /api/evidence, /api/admin)
        │
        ▼
  Next.js frontend — Priority Queue · County Detail · Evidence Trail ·
                      Backtest · Regional Map · Send Aid
```

---

## Running locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/` with at least:

```
GROQ_API_KEY=your_groq_key
NVIDIA_API_KEY=your_nvidia_key   # optional fallback
```

Then run:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`, with docs at `http://localhost:8000/docs`. Health check: `GET /health`.

### Frontend

```bash
cd frontend
npm install
```

Create a `.env.local` file in `frontend/` if the backend isn't running on the default:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then run:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

---

## API overview

| Prefix | Purpose |
|---|---|
| `/api/counties` | County list, detail, phase data |
| `/api/forecast` | Per-county forecasts, threshold crossings, priority queue |
| `/api/evidence` | Source-bulletin trail for every parsed value |
| `/api/admin` | Ingestion/scraper controls (no auth — see below) |

Full interactive docs at `/docs` once the backend is running.

---

## Notes on scope

- **No authentication.** This is a deliberate hackathon-scope decision, not an oversight — real auth wasn't what was being judged, and it's pure time cost for a build like this.
- **Send Aid is simulated.** No live SMS gateway is wired up; the exact message text is rendered and logged instead of dispatched. See [Send Aid](#send-aid--bilingual-crisis-alert-broadcasting) above.
- **Historical data (2022–2026)** was hand-compiled from publicly available past NDMA bulletins to fill gaps the live scraper can't reach behind NDMA's JS-driven archive filter, and never overrides a live-parsed record for the same county/month.

---

## Team

Built for the IGAD Hackathon 2026, hosted by ICPAC (IGAD Climate Predictions and Applications Centre).
