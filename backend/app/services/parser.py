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

# NDMA phase classifications
VALID_PHASES = {"Normal", "Alert", "Alarm", "Emergency", "Recovery"}

# VCI3M thresholds per NDMA classification
VCI3M_THRESHOLDS = {
    "Normal": 50.0,      # VCI3M >= 50
    "Alert": 35.0,       # 35 <= VCI3M < 50  (watch)
    "Alarm": 20.0,       # 20 <= VCI3M < 35  (moderate drought)
    "Emergency": 10.0,   # VCI3M < 20        (severe drought)
}

# SPI classification thresholds
SPI_THRESHOLDS = {
    "Normal": -0.5,
    "Alert": -1.0,
    "Alarm": -1.5,
    "Emergency": -2.0,
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
    """Extract phase classification from text."""
    for phase in VALID_PHASES:
        if phase.lower() in text.lower():
            return phase
    return None


def extract_vci3m(text: str) -> Optional[float]:
    """Extract VCI3M value from text."""
    patterns = [
        r'VCI[\s-]*3M[\s:]*(\d+\.?\d*)',
        r'VCI3M[\s:]*(\d+\.?\d*)',
        r'Vegetation\s+Condition\s+Index.*?(\d+\.?\d*)',
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
        r'SPI[\s:]*(-?\d+\.?\d*)',
        r'Standardized\s+Precipitation.*?(-?\d+\.?\d*)',
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
    """Classify drought phase from VCI3M value using NDMA thresholds."""
    if vci3m >= VCI3M_THRESHOLDS["Normal"]:
        return "Normal"
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
        "Alert": 2,
        "Alarm": 3,
        "Emergency": 4,
    }
    return severity_map.get(phase, 0)


def get_threshold_for_phase(phase: str) -> float:
    """Get the VCI3M threshold value for crossing into a given phase."""
    return VCI3M_THRESHOLDS.get(phase, 50.0)
