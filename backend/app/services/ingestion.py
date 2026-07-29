"""
NDMA Bulletin Ingestion Service

Fetches live county drought bulletins from NDMA KnowledgeWeb, then downloads
the official PDFs for parsing and evidence citation.
"""

import asyncio
import httpx
import os
import re
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Official NDMA KnowledgeWeb endpoints. The listing itself carries the latest
# set of published county bulletins, so no bulletin values or document IDs are
# embedded in the application.
NDMA_KNOWLEDGEWEB = "https://knowledgeweb.ndma.go.ke"
NDMA_COUNTY_BULLETINS_URL = (
    f"{NDMA_KNOWLEDGEWEB}/Public/Resources/CountyBulletins.aspx?ID=11"
)
NDMA_DOCUMENT_URL = f"{NDMA_KNOWLEDGEWEB}/Library/doclink.aspx?document={{document_id}}"

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

# NDMA's real 23 ASAL (Arid and Semi-Arid Lands) counties — the actual set
# covered by the National Drought Early Warning Bulletin. Kenya has 47
# counties total, but NDMA only monitors and publishes bulletins for these
# 23; the rest (Nairobi, Mombasa, Kiambu, etc.) never get a real bulletin,
# so keeping them in this list only produces permanently-empty county cards.
ALL_COUNTIES = [
    {"name": "Baringo", "region": "Rift Valley", "livelihood": "agro-pastoralist", "lat": 0.4917, "lon": 35.9585},
    {"name": "Embu", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": -0.5388, "lon": 37.4596},
    {"name": "Garissa", "region": "North Eastern", "livelihood": "pastoralist", "lat": -0.4532, "lon": 39.6461},
    {"name": "Isiolo", "region": "Eastern", "livelihood": "pastoralist", "lat": 0.3546, "lon": 37.5822},
    {"name": "Kajiado", "region": "Rift Valley", "livelihood": "pastoralist", "lat": -2.0981, "lon": 36.7820},
    {"name": "Kilifi", "region": "Coast", "livelihood": "agro-pastoralist", "lat": -3.5107, "lon": 39.9093},
    {"name": "Kitui", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": -1.3668, "lon": 38.0106},
    {"name": "Kwale", "region": "Coast", "livelihood": "agro-pastoralist", "lat": -4.1816, "lon": 39.4611},
    {"name": "Laikipia", "region": "Rift Valley", "livelihood": "agro-pastoralist", "lat": 0.2300, "lon": 36.8600},
    {"name": "Lamu", "region": "Coast", "livelihood": "agro-pastoralist", "lat": -2.2717, "lon": 40.9020},
    {"name": "Makueni", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": -1.8039, "lon": 37.6200},
    {"name": "Mandera", "region": "North Eastern", "livelihood": "pastoralist", "lat": 3.9373, "lon": 41.8569},
    {"name": "Marsabit", "region": "Eastern", "livelihood": "pastoralist", "lat": 2.3284, "lon": 37.9910},
    {"name": "Meru", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": 0.0474, "lon": 37.6559},
    {"name": "Narok", "region": "Rift Valley", "livelihood": "pastoralist", "lat": -1.0871, "lon": 35.8710},
    {"name": "Nyeri", "region": "Central", "livelihood": "agro-pastoralist", "lat": -0.4197, "lon": 36.9511},
    {"name": "Samburu", "region": "Rift Valley", "livelihood": "pastoralist", "lat": 1.2155, "lon": 36.9541},
    {"name": "Taita Taveta", "region": "Coast", "livelihood": "agro-pastoralist", "lat": -3.3961, "lon": 38.5548},
    {"name": "Tana River", "region": "Coast", "livelihood": "pastoralist", "lat": -1.7812, "lon": 39.6518},
    {"name": "Tharaka Nithi", "region": "Eastern", "livelihood": "agro-pastoralist", "lat": -0.2963, "lon": 37.7241},
    {"name": "Turkana", "region": "Rift Valley", "livelihood": "pastoralist", "lat": 3.1122, "lon": 35.5986},
    {"name": "Wajir", "region": "North Eastern", "livelihood": "pastoralist", "lat": 1.7471, "lon": 40.0573},
    {"name": "West Pokot", "region": "Rift Valley", "livelihood": "pastoralist", "lat": 1.6219, "lon": 35.2219},
]


async def fetch_bulletin_links() -> list[dict]:
    """Discover the currently published county-bulletin PDFs from NDMA.

    The public listing supplies both county and bulletin month. Each resource
    details link contains an NDMA document UUID, which is used to obtain the
    official PDF. No document URL, county status, or indicator value is stored
    as application data.
    """
    bulletins: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                NDMA_COUNTY_BULLETINS_URL,
                headers={"User-Agent": "Pulsecast/1.0 (drought-monitoring-research)"},
            )

        if response.status_code != 200:
            logger.warning("NDMA KnowledgeWeb returned %s", response.status_code)
            return bulletins

        soup = BeautifulSoup(response.text, "html.parser")
        seen_document_ids: set[str] = set()
        for link in soup.find_all("a", href=True):
            href = link["href"]
            document_match = re.search(
                r"ResourceDetails\.aspx\?doc=([0-9a-f-]{36})",
                href,
                re.IGNORECASE,
            )
            if not document_match:
                continue

            document_id = document_match.group(1).lower()
            if document_id in seen_document_ids:
                continue

            title = link.get_text(" ", strip=True)
            title_lower = title.lower()
            if (
                ("drought" not in title_lower and "dew" not in title_lower)
                or "bulletin" not in title_lower
            ):
                continue

            county_name = _county_from_title(title)
            month = next(
                (number for name, number in MONTH_NAMES.items() if name in title_lower),
                None,
            )
            year_match = re.search(r"\b(20\d{2})\b", title)
            if not county_name or not month or not year_match:
                logger.warning("Skipping NDMA bulletin with incomplete metadata: %s", title)
                continue

            year = int(year_match.group(1))
            safe_county = re.sub(r"[^a-z0-9]+", "-", county_name.lower()).strip("-")
            seen_document_ids.add(document_id)
            bulletins.append({
                "url": NDMA_DOCUMENT_URL.format(document_id=document_id),
                "details_url": urljoin(str(response.url), href),
                "filename": f"{year}-{month:02d}-{safe_county}-{document_id}.pdf",
                "county_name": county_name,
                "month": f"{year}-{month:02d}",
                "title": title,
            })

        logger.info("Found %s live county bulletins on NDMA KnowledgeWeb", len(bulletins))
    except httpx.HTTPError as exc:
        logger.warning("Could not reach NDMA KnowledgeWeb: %s", exc)
    except Exception as exc:
        logger.error("Error scraping NDMA KnowledgeWeb: %s", exc)

    return bulletins


def _county_from_title(title: str) -> Optional[str]:
    """Resolve an NDMA listing title to one of the county metadata names."""
    normalized_title = re.sub(r"[^a-z]", "", title.lower())
    for county in ALL_COUNTIES:
        normalized_county = re.sub(r"[^a-z]", "", county["name"].lower())
        if normalized_county in normalized_title:
            return county["name"]
    return None


async def download_bulletin(
    url: str,
    save_dir: str = "data/bulletins",
    filename: Optional[str] = None,
) -> Optional[str]:
    """
    Download a single NDMA bulletin PDF.
    Returns the local file path if successful, None otherwise.
    """
    os.makedirs(save_dir, exist_ok=True)
    filename = filename or f"{url.split('document=')[-1].split('&')[0]}.pdf"
    filepath = Path(save_dir) / filename

    # Skip if already downloaded
    if filepath.exists() and filepath.stat().st_size > 1000:
        logger.info("Bulletin already cached: %s", filepath)
        return str(filepath)

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Pulsecast/1.0 (drought-monitoring-research)"}
            )

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type or response.content[:4] == b"%PDF":
                    with filepath.open("wb") as f:
                        f.write(response.content)
                    logger.info("Downloaded bulletin: %s (%s bytes)", filepath, len(response.content))
                    return str(filepath)
                else:
                    logger.warning("URL did not return a PDF: %s (content-type: %s)", url, content_type)
            else:
                logger.warning("Download failed with status %s: %s", response.status_code, url)

    except httpx.HTTPError as e:
        logger.warning("Download error for %s: %s", url, e)
    except Exception as e:
        logger.error("Unexpected error downloading %s: %s", url, e)

    return None


async def ingest_all_bulletins(save_dir: str = "data/bulletins") -> list[dict]:
    """
    Full ingestion pipeline: discover NDMA records and download their PDFs.

    Each result retains the official source URL and listing metadata alongside
    its local cache path so the database can cite exactly what was parsed.
    """
    links = await fetch_bulletin_links()
    semaphore = asyncio.Semaphore(4)

    async def download_one(bulletin: dict) -> Optional[dict]:
        async with semaphore:
            path = await download_bulletin(
                bulletin["url"], save_dir, filename=bulletin["filename"]
            )
        return {**bulletin, "path": path} if path else None

    downloaded = [
        bulletin
        for bulletin in await asyncio.gather(*(download_one(link) for link in links))
        if bulletin is not None
    ]

    logger.info("Ingested %s bulletins out of %s NDMA records", len(downloaded), len(links))
    return downloaded
