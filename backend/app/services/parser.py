"""
PDF Parser Service

Extracts per-county drought data from NDMA bulletin PDFs:
  - Phase classification (Normal, Alert, Alarm, Emergency, Recovery)
  - VCI3M (Vegetation Condition Index, 3-month average)
  - SPI (Standardized Precipitation Index)
  
Uses pdfplumber for text/table extraction from the structured NDMA format.
"""

import pdfplumber
import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# NDMA phase classifications. NDMA's actual National bulletins (confirmed
# against the Jan 2026 and Feb 2026 editions) use six phases, not five —
# "Pre-Alert" sits between Normal and Alert. It's a real, currently-used
# label, not a hypothetical.
VALID_PHASES = {"Normal", "Pre-Alert", "Alert", "Alarm", "Emergency", "Recovery"}

# NDMA's VCI3M vegetation-condition bands, confirmed in current county
# bulletins. These are a VCI proxy for forecasting; NDMA's official EW phase
# remains the multi-indicator phase printed in each bulletin.
# Pre-Alert has no published numeric VCI3M cutoff of its own (NDMA assigns it
# via multi-indicator judgement, not a single VCI3M number) — 27.5 here is an
# interpolated midpoint between Alert and Normal, used only as a fallback
# when a bulletin's phase can't be read directly from its own text.
VCI3M_THRESHOLDS = {
    "Normal": 35.0,      # normal / above-normal vegetation condition
    "Pre-Alert": 27.5,   # interpolated midpoint (see note above)
    "Alert": 20.0,       # moderate vegetation deficit
    "Alarm": 10.0,       # severe vegetation deficit
    "Emergency": 0.0,    # extreme vegetation deficit
}

# Known county name variations in bulletins
COUNTY_ALIASES = {
    "taita-taveta": "Taita Taveta",
    "tana river": "Tana River",
    "tharaka-nithi": "Tharaka Nithi",
    "tharaka nithi": "Tharaka Nithi",
    "west pokot": "West Pokot",
    "homa bay": "Homa Bay",
    "trans nzoia": "Trans Nzoia",
    "uasin gishu": "Uasin Gishu",
    "elgeyo-marakwet": "Elgeyo Marakwet",
    "elgeyo marakwet": "Elgeyo Marakwet",
    "murang'a": "Murang'a",
    "muranga": "Murang'a",
}


def normalize_county_name(name: str) -> str:
    """Normalize county name to match our database."""
    clean = name.strip().lower()
    if clean in COUNTY_ALIASES:
        return COUNTY_ALIASES[clean]
    return name.strip().title()


def extract_phase(text: str) -> Optional[str]:
    """Extract phase classification from text.

    Longest phase name first — 'Alert' is a literal substring of
    'Pre-Alert', so checking in the wrong order would misclassify every
    Pre-Alert bulletin as Alert.
    """
    for phase in sorted(VALID_PHASES, key=len, reverse=True):
        if phase.lower() in text.lower():
            return phase
    return None


def extract_vci3m(text: str) -> Optional[float]:
    """Extract VCI3M value from text."""
    patterns = [
        r'VCI\s*\(\s*3\s*Months?\s*\)[\s:]*(\d+\.?\d*)',
        r'VCI[\s-]*(?:3\s*Months?|3M)[\s:]*(\d+\.?\d*)',
        r'3\s*[- ]?month\s+VCI\s+(?:of|was|stood at)\s*(\d+\.?\d*)',
        r'\bVCI(?!\s*-\s*3\b)\s*[:\-]?\s*(\d+\.?\d*)',
        r'Vegetation\s+Condition\s+Index[\s:]*(\d+\.?\d*)',
        r'Vegetation\s+Condition\s+Index\s+(?:averaged|was|stood at)\s*(\d+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if 0 <= val <= 100:  # Valid VCI range
                return val
    return None


def extract_spi(text: str) -> Optional[float]:
    """Extract SPI value from text."""
    patterns = [
        r'SPI\s*[-–]?\s*3\s*Months?[\s:]*(-?\d+\.?\d*)',
        r'SPI[\s:]*(-?\d+\.?\d*)',
        r'Standardized\s+Precipitation\s+Index[\s:]*(-?\d+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if -4 <= val <= 4:  # Valid SPI range
                return val
    return None


def extract_date_from_text(text: str) -> Optional[str]:
    """Extract bulletin date (month/year) from text."""
    patterns = [
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        r'(\d{1,2})[/-](\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                try:
                    if groups[0].isdigit():
                        return f"{groups[1]}-{int(groups[0]):02d}"
                    else:
                        dt = datetime.strptime(f"{groups[0]} {groups[1]}", "%B %Y")
                        return dt.strftime("%Y-%m")
                except ValueError:
                    continue
    return None


def parse_bulletin_tables(pdf_path: str) -> list[dict]:
    """
    Parse structured tables from an NDMA bulletin PDF.
    
    NDMA bulletins typically contain summary tables with columns like:
    County | Phase | VCI3M | SPI | Trend
    """
    records = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            bulletin_date = None
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                
                # Try to get bulletin date from first page
                if not bulletin_date:
                    bulletin_date = extract_date_from_text(text)
                
                # Extract tables
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # Find header row
                    header = table[0]
                    if not header:
                        continue
                    
                    header_lower = [str(h).lower() if h else "" for h in header]
                    
                    # Look for relevant columns
                    county_col = None
                    phase_col = None
                    vci_col = None
                    spi_col = None
                    
                    for i, h in enumerate(header_lower):
                        if "county" in h or "sub-county" in h:
                            county_col = i
                        elif "phase" in h or "classification" in h or "status" in h:
                            phase_col = i
                        elif "vci" in h:
                            vci_col = i
                        elif "spi" in h:
                            spi_col = i
                    
                    if county_col is None:
                        continue
                    
                    # Parse data rows
                    for row in table[1:]:
                        if not row or len(row) <= county_col:
                            continue
                        
                        county_name = str(row[county_col]).strip() if row[county_col] else None
                        if not county_name or county_name.lower() in ("", "total", "average", "county"):
                            continue
                        
                        county_name = normalize_county_name(county_name)
                        
                        record = {
                            "county_name": county_name,
                            "month": bulletin_date or datetime.now().strftime("%Y-%m"),
                            "phase": None,
                            "vci3m": None,
                            "spi": None,
                            "source_page": page_num + 1,
                        }
                        
                        if phase_col is not None and len(row) > phase_col and row[phase_col]:
                            record["phase"] = extract_phase(str(row[phase_col]))
                        
                        if vci_col is not None and len(row) > vci_col and row[vci_col]:
                            try:
                                record["vci3m"] = float(str(row[vci_col]).strip())
                            except ValueError:
                                record["vci3m"] = extract_vci3m(str(row[vci_col]))
                        
                        if spi_col is not None and len(row) > spi_col and row[spi_col]:
                            try:
                                record["spi"] = float(str(row[spi_col]).strip())
                            except ValueError:
                                record["spi"] = extract_spi(str(row[spi_col]))
                        
                        # If no phase from table, infer from VCI3M
                        if record["phase"] is None and record["vci3m"] is not None:
                            record["phase"] = classify_from_vci3m(record["vci3m"])
                        
                        if record["phase"]:
                            records.append(record)
                
                # If no tables found, try text-based extraction
                if not records:
                    text_records = parse_bulletin_text(text, page_num + 1, bulletin_date)
                    records.extend(text_records)
    
    except Exception as e:
        logger.error(f"Error parsing PDF {pdf_path}: {e}")
    
    logger.info(f"Parsed {len(records)} records from {pdf_path}")
    return records


def parse_county_bulletin(
    pdf_path: str,
    county_name: str,
    bulletin_month: str,
) -> Optional[dict]:
    """Extract the county summary from one official NDMA county bulletin.

    County bulletins publish the official EW phase and VCI3M in their first
    page summary, but their table headers vary by county. Parsing the document
    as a single-county bulletin avoids inventing values when a table layout
    changes.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # The county summary and indicator table are on page one. Reading
            # subsequent chart pages can capture unrelated axis labels.
            page = pdf.pages[0]
            text = page.extract_text() or ""
            table_vci3m = _extract_vci3m_from_summary_table(page)
    except Exception as exc:
        logger.error("Could not read county bulletin %s: %s", pdf_path, exc)
        return None

    # Typical extracted text: "County  Alert  Deteriorating". Restrict the
    # match to the county summary row rather than accepting an incidental
    # occurrence of a phase name elsewhere in the document.
    phase_summary = text.split("Drought Situation", maxsplit=1)[0]
    phase_match = re.search(
        r"\bC\s*ounty\s*(?:\n|\s)+(Normal|Alert|Alarm|Emergency|Recovery)\b",
        phase_summary,
        re.IGNORECASE,
    )
    phase = phase_match.group(1).title() if phase_match else None
    if not phase:
        # Some county templates use a local county label (for example,
        # "Kieni") rather than the word County in the final summary row.
        phases = re.findall(
            r"\b(Normal|Alert|Alarm|Emergency|Recovery)\b\s+"
            r"(?:Stable|Worsening|Improving|Deteriorating)\b",
            phase_summary,
            re.IGNORECASE,
        )
        phase = phases[-1].title() if phases else None
    if not phase:
        logger.warning("No official EW phase found in %s; skipping it", pdf_path)
        return None

    return {
        "county_name": normalize_county_name(county_name),
        "month": bulletin_month,
        "phase": phase,
        "vci3m": table_vci3m if table_vci3m is not None else extract_vci3m(text),
        "spi": extract_spi(text),
        "source_page": 1,
    }


def _extract_page_one_text(pdf_path: str) -> Optional[str]:
    """Read raw page-1 text only — used to hand a failed bulletin to the AI
    parsing fallback without re-deriving anything from it ourselves."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return pdf.pages[0].extract_text() or ""
    except Exception as exc:
        logger.error("Could not read page text from %s: %s", pdf_path, exc)
        return None


async def parse_county_bulletin_with_ai_fallback(
    pdf_path: str,
    county_name: str,
    bulletin_month: str,
) -> Optional[dict]:
    """
    Try the deterministic regex/table parser first; only reach for the AI
    fallback when that finds no phase at all — for example a county whose
    bulletin template this quarter doesn't match any of the known patterns.

    The AI never sees a bulletin the regex parser already succeeded on, and
    its output is discarded unless it grounds every claim in a verbatim quote
    from the page (see llm.extract_bulletin_fields_ai). Returns a record
    tagged with parsing_method so the evidence trail always shows which path
    produced it — this is a recovery path for parser drift, not a silent
    replacement for the deterministic parser.
    """
    record = parse_county_bulletin(pdf_path, county_name, bulletin_month)
    if record:
        record["parsing_method"] = "regex"
        record["ai_evidence"] = None
        return record

    page_text = _extract_page_one_text(pdf_path)
    if not page_text:
        return None

    from app.services.llm import extract_bulletin_fields_ai

    ai_result = await extract_bulletin_fields_ai(county_name, page_text)
    if not ai_result:
        logger.warning(
            "Regex parser and AI fallback both failed to find a phase in %s; skipping it",
            pdf_path,
        )
        return None

    logger.info("AI parsing fallback recovered a phase for %s (%s)", county_name, bulletin_month)
    return {
        "county_name": normalize_county_name(county_name),
        "month": bulletin_month,
        "phase": ai_result["phase"],
        "vci3m": ai_result["vci3m"],
        "spi": ai_result["spi"],
        "source_page": 1,
        "parsing_method": "ai_fallback",
        "ai_evidence": ai_result["evidence"],
    }


def _extract_vci3m_from_summary_table(page) -> Optional[float]:
    """Read VCI3M from a first-page NDMA summary table when available."""
    try:
        for table in page.extract_tables():
            for row in table or []:
                cells = [str(cell).strip().replace("\n", " ") if cell else "" for cell in row]
                for index, cell in enumerate(cells):
                    if not re.match(r"^(?:VCI|Vegetation Condition(?: Index)?)\b", cell, re.IGNORECASE):
                        continue
                    for value_cell in cells[index + 1:]:
                        value_match = re.fullmatch(r"(\d+(?:\.\d+)?)%?", value_cell)
                        if value_match:
                            value = float(value_match.group(1))
                            if 0 <= value <= 100:
                                return value
    except Exception as exc:
        logger.debug("Could not extract VCI3M table value: %s", exc)
    return None


def parse_bulletin_text(text: str, page_num: int, bulletin_date: Optional[str] = None) -> list[dict]:
    """
    Fallback: extract county data from unstructured text when tables aren't found.
    """
    records = []
    
    from app.services.ingestion import ALL_COUNTIES
    county_names = [c["name"] for c in ALL_COUNTIES]
    
    for county_name in county_names:
        # Look for county name followed by relevant data
        pattern = rf'{re.escape(county_name)}[:\s]+.*?(?:phase|status|classification)[:\s]*(Normal|Alert|Alarm|Emergency|Recovery)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            phase = match.group(1).title()
            vci3m = extract_vci3m(text[match.start():match.start()+500])
            spi = extract_spi(text[match.start():match.start()+500])
            
            records.append({
                "county_name": county_name,
                "month": bulletin_date or datetime.now().strftime("%Y-%m"),
                "phase": phase,
                "vci3m": vci3m,
                "spi": spi,
                "source_page": page_num,
            })
    
    return records


def classify_from_vci3m(vci3m: float) -> str:
    """Return the NDMA VCI3M vegetation-condition proxy band."""
    if vci3m >= VCI3M_THRESHOLDS["Normal"]:
        return "Normal"
    elif vci3m >= VCI3M_THRESHOLDS["Pre-Alert"]:
        return "Pre-Alert"
    elif vci3m >= VCI3M_THRESHOLDS["Alert"]:
        return "Alert"
    elif vci3m >= VCI3M_THRESHOLDS["Alarm"]:
        return "Alarm"
    else:
        return "Emergency"


def get_phase_severity(phase: str) -> int:
    """Return numeric severity for a phase (higher = worse)."""
    severity_map = {
        "Normal": 0,
        "Recovery": 1,
        "Pre-Alert": 2,
        "Alert": 3,
        "Alarm": 4,
        "Emergency": 5,
    }
    return severity_map.get(phase, 0)


def get_threshold_for_phase(phase: str) -> float:
    """Get the VCI3M threshold value for crossing into a given phase."""
    return VCI3M_THRESHOLDS.get(phase, 50.0)
