"""
Database layer — async SQLite via aiosqlite.

Tables:
  - counties: static metadata (name, region, livelihood zone)
  - bulletins: parsed NDMA bulletin records ({county, month, VCI3M, SPI, phase})
  - forecasts: cached forecasts with confidence intervals
"""

import aiosqlite
import os
from app.config import settings

DB_PATH = settings.DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS counties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    region TEXT NOT NULL,
    livelihood_zone TEXT NOT NULL DEFAULT 'mixed',
    latitude REAL,
    longitude REAL
);

CREATE TABLE IF NOT EXISTS bulletins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    county_id INTEGER NOT NULL,
    month TEXT NOT NULL,          -- YYYY-MM format
    vci3m REAL,
    spi REAL,
    phase TEXT NOT NULL,          -- Normal, Alert, Alarm, Emergency, Recovery
    source_url TEXT,
    source_page INTEGER,
    parsed_at TEXT NOT NULL,      -- ISO timestamp
    parsing_method TEXT NOT NULL DEFAULT 'regex',  -- 'regex' or 'ai_fallback' — see parser.py
    ai_evidence TEXT,             -- verbatim source quote the AI cited, only set when parsing_method = 'ai_fallback'
    FOREIGN KEY (county_id) REFERENCES counties(id),
    UNIQUE(county_id, month)
);

CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    county_id INTEGER NOT NULL,
    generated_at TEXT NOT NULL,
    forecast_weeks INTEGER NOT NULL DEFAULT 6,
    forecast_values TEXT NOT NULL,       -- JSON array of {week, vci3m, lower, upper}
    crossing_date TEXT,                  -- estimated threshold crossing date or null
    crossing_phase TEXT,                 -- phase it would cross into
    days_to_crossing INTEGER,
    confidence REAL,
    priority_score REAL,
    ai_explanation TEXT,
    pattern_signals TEXT,                -- JSON: cross-county/temporal pattern detections (see patterns.py)
    FOREIGN KEY (county_id) REFERENCES counties(id)
);

CREATE INDEX IF NOT EXISTS idx_bulletins_county ON bulletins(county_id);
CREATE INDEX IF NOT EXISTS idx_bulletins_month ON bulletins(month);
CREATE INDEX IF NOT EXISTS idx_forecasts_county ON forecasts(county_id);
CREATE INDEX IF NOT EXISTS idx_forecasts_generated ON forecasts(generated_at);
"""


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Initialize the database schema."""
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await _migrate_schema(db)
        await db.commit()
    finally:
        await db.close()


async def _migrate_schema(db: aiosqlite.Connection) -> None:
    """Add columns introduced after a DB file was first created.

    `CREATE TABLE IF NOT EXISTS` in SCHEMA only applies to brand-new
    databases — existing SQLite files on disk (e.g. a prior deployment's
    volume) keep whatever columns they had at creation time. This adds any
    columns that are missing without touching existing data.
    """
    cursor = await db.execute("PRAGMA table_info(forecasts)")
    existing_columns = {row["name"] for row in await cursor.fetchall()}

    if "pattern_signals" not in existing_columns:
        await db.execute("ALTER TABLE forecasts ADD COLUMN pattern_signals TEXT")

    cursor = await db.execute("PRAGMA table_info(bulletins)")
    existing_bulletin_columns = {row["name"] for row in await cursor.fetchall()}

    if "parsing_method" not in existing_bulletin_columns:
        await db.execute(
            "ALTER TABLE bulletins ADD COLUMN parsing_method TEXT NOT NULL DEFAULT 'regex'"
        )
    if "ai_evidence" not in existing_bulletin_columns:
        await db.execute("ALTER TABLE bulletins ADD COLUMN ai_evidence TEXT")


async def execute_query(query: str, params: tuple = (), fetchone: bool = False):
    """Execute a query and return results."""
    db = await get_db()
    try:
        cursor = await db.execute(query, params)
        if fetchone:
            row = await cursor.fetchone()
            return dict(row) if row else None
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def execute_insert(query: str, params: tuple = ()) -> int:
    """Execute an insert and return the last row ID."""
    db = await get_db()
    try:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def execute_many(query: str, params_list: list[tuple]):
    """Execute many inserts in a batch."""
    db = await get_db()
    try:
        await db.executemany(query, params_list)
        await db.commit()
    finally:
        await db.close()
