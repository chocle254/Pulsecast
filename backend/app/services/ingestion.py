"""
NDMA Bulletin Ingestion Service — REAL DATA

Fetches actual monthly drought bulletins from NDMA's website.
NDMA publishes per-county drought early warning bulletins as PDFs at:
  https://www.ndma.go.ke/index.php/resource-center/category/12-drought-updates

This service:
1. Scrapes the NDMA resource center for available PDF bulletin links
2. Downloads each PDF to a local cache directory
3. Passes them to the parser for structured data extraction
"""

import httpx
import os
import re
import logging
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# NDMA official website
NDMA_MAIN_SITE = "https://www.ndma.go.ke"
NDMA_RESOURCE_CENTER = f"{NDMA_MAIN_SITE}/index.php/resource-center/category/12-drought-updates"

# All 47 Kenya counties with metadata
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


async def fetch_bulletin_links() -> list[dict]:
    """
    Scrape the NDMA resource center page for all available drought bulletin PDFs.
    Returns a list of {url, filename, year, month}.
    """
    bulletins = []

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                NDMA_RESOURCE_CENTER,
                headers={"User-Agent": "Pulsecast/1.0 (drought-monitoring-research)"}
            )

            if response.status_code != 200:
                logger.warning(f"NDMA resource center returned {response.status_code}")
                return bulletins

            soup = BeautifulSoup(response.text, "html.parser")

            # NDMA uses Joomla — bulletin PDFs are typically in download links
            for link in soup.find_all("a", href=True):
                href = link["href"]

                # Look for PDF download links
                if "/send/" in href or href.lower().endswith(".pdf"):
                    url = href if href.startswith("http") else f"{NDMA_MAIN_SITE}{href}"

                    # Extract date from link text or URL
                    text = link.get_text(strip=True).lower()
                    full = f"{text} {url}".lower()

                    # Try to extract year-month
                    month_names = {
                        "january": 1, "february": 2, "march": 3, "april": 4,
                        "may": 5, "june": 6, "july": 7, "august": 8,
                        "september": 9, "october": 10, "november": 11, "december": 12
                    }

                    year = None
                    month = None

                    # Match "Month YYYY" or "YYYY Month"
                    for mname, mnum in month_names.items():
                        if mname in full:
                            month = mnum
                            break

                    year_match = re.search(r'20[12]\d', full)
                    if year_match:
                        year = int(year_match.group())

                    if not year:
                        year = datetime.now().year

                    filename = url.split("/")[-1]
                    if not filename.endswith(".pdf"):
                        filename = f"bulletin_{year}_{month or 0:02d}.pdf"

                    bulletins.append({
                        "url": url,
                        "filename": filename,
                        "year": year,
                        "month": month,
                        "title": link.get_text(strip=True),
                    })

            logger.info(f"Found {len(bulletins)} bulletin links from NDMA resource center")

    except httpx.HTTPError as e:
        logger.warning(f"Could not reach NDMA website: {e}")
    except Exception as e:
        logger.error(f"Error scraping NDMA resource center: {e}")

    return bulletins


async def download_bulletin(url: str, save_dir: str = "data/bulletins") -> Optional[str]:
    """
    Download a single NDMA bulletin PDF.
    Returns the local file path if successful, None otherwise.
    """
    os.makedirs(save_dir, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    filepath = os.path.join(save_dir, filename)

    # Skip if already downloaded
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        logger.info(f"Bulletin already cached: {filepath}")
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
                    logger.info(f"Downloaded bulletin: {filepath} ({len(response.content)} bytes)")
                    return filepath
                else:
                    logger.warning(f"URL did not return a PDF: {url} (content-type: {content_type})")
            else:
                logger.warning(f"Download failed with status {response.status_code}: {url}")

    except httpx.HTTPError as e:
        logger.warning(f"Download error for {url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}")

    return None


async def ingest_all_bulletins(save_dir: str = "data/bulletins") -> list[str]:
    """
    Full ingestion pipeline: scrape NDMA → download PDFs → return local paths.
    """
    links = await fetch_bulletin_links()
    downloaded = []

    for bulletin in links:
        path = await download_bulletin(bulletin["url"], save_dir)
        if path:
            downloaded.append(path)

    logger.info(f"Ingested {len(downloaded)} bulletins out of {len(links)} links found")
    return downloaded
