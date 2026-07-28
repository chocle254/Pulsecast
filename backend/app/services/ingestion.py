"""
NDMA Bulletin Ingestion Service

Fetches monthly drought bulletins from NDMA's KnowledgeWeb portal,
downloads the PDFs, and stores them locally for parsing.
"""

import httpx
import os
import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# NDMA KnowledgeWeb bulletin URLs follow this pattern
NDMA_KNOWLEDGE_WEB = "https://knowledgeweb.ndma.go.ke"
NDMA_BULLETINS_API = f"{NDMA_KNOWLEDGE_WEB}/api/drought-bulletins"
NDMA_MAIN_SITE = "https://www.ndma.go.ke"
NDMA_RESOURCE_CENTER = f"{NDMA_MAIN_SITE}/index.php/resource-center/send"

# Known ASAL (Arid and Semi-Arid Lands) counties with drought monitoring
ASAL_COUNTIES = [
    "Baringo", "Garissa", "Isiolo", "Kajiado", "Kilifi", "Kitui",
    "Kwale", "Laikipia", "Lamu", "Makueni", "Mandera", "Marsabit",
    "Meru", "Narok", "Nyeri", "Samburu", "Taita Taveta", "Tana River",
    "Tharaka Nithi", "Turkana", "Wajir", "West Pokot", "Embu",
]

# All 47 Kenya counties for the map view
ALL_COUNTIES = [
    {"name": "Baringo", "region": "Rift Valley", "livelihood": "agro-pastoralist", "lat": 0.4917, "lon": 35.9585},
    {"name": "Bomet", "region": "Rift Valley", "livelihood": "mixed", "lat": -0.7813, "lon": 35.3416},
    {"name": "Bungoma", "region": "Western", "livelihood": "mixed", "lat": 0.5695, "lon": 34.5584},
    {"name": "Busia", "region": "Western", "livelihood": "mixed", "lat": 0.4347, "lon": 34.2422},
    {"name": "Elgeyo Marakwet", "region": "Rift Valley", "livelihood": "mixed", "lat": 0.8678, "lon": 35.5271},
    {"name": "Embu", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": -0.5388, "lon": 37.4596},
    {"name": "Garissa", "region": "North Eastern", "livelihood": "pastoralist", "lat": -0.4532, "lon": 39.6461},
    {"name": "Homa Bay", "region": "Nyanza", "livelihood": "mixed", "lat": -0.5273, "lon": 34.4571},
    {"name": "Isiolo", "region": "Eastern", "livelihood": "pastoralist", "lat": 0.3546, "lon": 37.5822},
    {"name": "Kajiado", "region": "Rift Valley", "livelihood": "pastoralist", "lat": -2.0981, "lon": 36.7820},
    {"name": "Kakamega", "region": "Western", "livelihood": "mixed", "lat": 0.2827, "lon": 34.7519},
    {"name": "Kericho", "region": "Rift Valley", "livelihood": "mixed", "lat": -0.3692, "lon": 35.2863},
    {"name": "Kiambu", "region": "Central", "livelihood": "mixed", "lat": -1.1714, "lon": 36.8356},
    {"name": "Kilifi", "region": "Coast", "livelihood": "agro-pastoralist", "lat": -3.5107, "lon": 39.9093},
    {"name": "Kirinyaga", "region": "Central", "livelihood": "mixed", "lat": -0.4989, "lon": 37.2803},
    {"name": "Kisii", "region": "Nyanza", "livelihood": "mixed", "lat": -0.6813, "lon": 34.7668},
    {"name": "Kisumu", "region": "Nyanza", "livelihood": "mixed", "lat": -0.1022, "lon": 34.7617},
    {"name": "Kitui", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": -1.3668, "lon": 38.0106},
    {"name": "Kwale", "region": "Coast", "livelihood": "agro-pastoralist", "lat": -4.1816, "lon": 39.4611},
    {"name": "Laikipia", "region": "Rift Valley", "livelihood": "agro-pastoralist", "lat": 0.2300, "lon": 36.8600},
    {"name": "Lamu", "region": "Coast", "livelihood": "agro-pastoralist", "lat": -2.2717, "lon": 40.9020},
    {"name": "Machakos", "region": "Eastern", "livelihood": "mixed", "lat": -1.5177, "lon": 37.2634},
    {"name": "Makueni", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": -1.8039, "lon": 37.6200},
    {"name": "Mandera", "region": "North Eastern", "livelihood": "pastoralist", "lat": 3.9373, "lon": 41.8569},
    {"name": "Marsabit", "region": "Eastern", "livelihood": "pastoralist", "lat": 2.3284, "lon": 37.9910},
    {"name": "Meru", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": 0.0474, "lon": 37.6559},
    {"name": "Migori", "region": "Nyanza", "livelihood": "mixed", "lat": -1.0634, "lon": 34.4731},
    {"name": "Mombasa", "region": "Coast", "livelihood": "mixed", "lat": -4.0435, "lon": 39.6682},
    {"name": "Murang'a", "region": "Central", "livelihood": "mixed", "lat": -0.7210, "lon": 37.1526},
    {"name": "Nairobi", "region": "Nairobi", "livelihood": "mixed", "lat": -1.2921, "lon": 36.8219},
    {"name": "Nakuru", "region": "Rift Valley", "livelihood": "mixed", "lat": -0.3031, "lon": 36.0800},
    {"name": "Nandi", "region": "Rift Valley", "livelihood": "mixed", "lat": 0.1836, "lon": 35.1269},
    {"name": "Narok", "region": "Rift Valley", "livelihood": "pastoralist", "lat": -1.0871, "lon": 35.8710},
    {"name": "Nyamira", "region": "Nyanza", "livelihood": "mixed", "lat": -0.5633, "lon": 34.9341},
    {"name": "Nyandarua", "region": "Central", "livelihood": "mixed", "lat": -0.1804, "lon": 36.5230},
    {"name": "Nyeri", "region": "Central", "livelihood": "agro-pastoralist", "lat": -0.4197, "lon": 36.9511},
    {"name": "Samburu", "region": "Rift Valley", "livelihood": "pastoralist", "lat": 1.2155, "lon": 36.9541},
    {"name": "Siaya", "region": "Nyanza", "livelihood": "mixed", "lat": -0.0617, "lon": 34.2422},
    {"name": "Taita Taveta", "region": "Coast", "livelihood": "agro-pastoralist", "lat": -3.3961, "lon": 38.5548},
    {"name": "Tana River", "region": "Coast", "livelihood": "pastoralist", "lat": -1.7812, "lon": 39.6518},
    {"name": "Tharaka Nithi", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": -0.2963, "lon": 37.7241},
    {"name": "Trans Nzoia", "region": "Rift Valley", "livelihood": "mixed", "lat": 1.0567, "lon": 34.9507},
    {"name": "Turkana", "region": "Rift Valley", "livelihood": "pastoralist", "lat": 3.1122, "lon": 35.5986},
    {"name": "Uasin Gishu", "region": "Rift Valley", "livelihood": "mixed", "lat": 0.5528, "lon": 35.3027},
    {"name": "Vihiga", "region": "Western", "livelihood": "mixed", "lat": 0.0829, "lon": 34.7233},
    {"name": "Wajir", "region": "North Eastern", "livelihood": "pastoralist", "lat": 1.7471, "lon": 40.0573},
    {"name": "West Pokot", "region": "Rift Valley", "livelihood": "pastoralist", "lat": 1.6219, "lon": 35.2219},
]


async def fetch_bulletin_list(year: Optional[int] = None, month: Optional[int] = None) -> list[dict]:
    """
    Fetch the list of available NDMA drought bulletins.
    
    Attempts to scrape the NDMA KnowledgeWeb portal for available PDFs.
    Falls back to constructing known URL patterns if the API is unavailable.
    """
    bulletins = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Try the KnowledgeWeb API first
            response = await client.get(
                f"{NDMA_MAIN_SITE}/index.php/resource-center/category/12-drought-updates",
                headers={"User-Agent": "Pulsecast/1.0 (drought-monitoring-research)"}
            )
            
            if response.status_code == 200:
                # Parse the page for PDF links
                content = response.text
                # Look for PDF download links
                pdf_pattern = r'href="([^"]*\.pdf[^"]*)"'
                matches = re.findall(pdf_pattern, content, re.IGNORECASE)
                
                for url in matches:
                    if not url.startswith("http"):
                        url = f"{NDMA_MAIN_SITE}{url}"
                    
                    # Try to extract date from URL or filename
                    date_match = re.search(r'(\d{4})[-_]?(\d{2})', url)
                    if date_match:
                        b_year = int(date_match.group(1))
                        b_month = int(date_match.group(2))
                        
                        if year and b_year != year:
                            continue
                        if month and b_month != month:
                            continue
                        
                        bulletins.append({
                            "url": url,
                            "year": b_year,
                            "month": b_month,
                            "filename": url.split("/")[-1]
                        })
                    
                logger.info(f"Found {len(bulletins)} bulletins from NDMA website")
            else:
                logger.warning(f"NDMA website returned status {response.status_code}")
                
    except httpx.HTTPError as e:
        logger.warning(f"Could not reach NDMA website: {e}")
    except Exception as e:
        logger.error(f"Error fetching bulletin list: {e}")
    
    # If no bulletins found, try known URL patterns for recent months
    if not bulletins:
        logger.info("Falling back to constructed bulletin URLs")
        target_year = year or datetime.now().year
        months_to_try = [month] if month else list(range(1, 13))
        
        for m in months_to_try:
            # Common NDMA URL patterns
            month_name = datetime(target_year, m, 1).strftime("%B").lower()
            patterns = [
                f"{NDMA_MAIN_SITE}/index.php/resource-center/send/12-drought-updates/{target_year}-{m:02d}-drought-bulletin",
                f"{NDMA_KNOWLEDGE_WEB}/drought-bulletins/{target_year}/{month_name}",
            ]
            
            for url in patterns:
                bulletins.append({
                    "url": url,
                    "year": target_year,
                    "month": m,
                    "filename": f"drought_bulletin_{target_year}_{m:02d}.pdf"
                })
    
    return bulletins


async def download_bulletin(url: str, save_dir: str = "data/bulletins") -> Optional[str]:
    """
    Download a single NDMA bulletin PDF.
    
    Returns the local file path if successful, None otherwise.
    """
    os.makedirs(save_dir, exist_ok=True)
    filename = url.split("/")[-1]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    
    filepath = os.path.join(save_dir, filename)
    
    # Skip if already downloaded
    if os.path.exists(filepath):
        logger.info(f"Bulletin already downloaded: {filepath}")
        return filepath
    
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Pulsecast/1.0 (drought-monitoring-research)"}
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type or response.content[:4] == b"%PDF":
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    logger.info(f"Downloaded bulletin: {filepath}")
                    return filepath
                else:
                    logger.warning(f"URL did not return a PDF: {url}")
            else:
                logger.warning(f"Download failed with status {response.status_code}: {url}")
                
    except httpx.HTTPError as e:
        logger.warning(f"Download error for {url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}")
    
    return None


async def ingest_bulletins(year: Optional[int] = None, month: Optional[int] = None) -> list[str]:
    """
    Full ingestion pipeline: fetch list → download PDFs → return local paths.
    """
    bulletins = await fetch_bulletin_list(year, month)
    downloaded = []
    
    for bulletin in bulletins:
        path = await download_bulletin(bulletin["url"])
        if path:
            downloaded.append(path)
    
    logger.info(f"Ingested {len(downloaded)} bulletins")
    return downloaded
