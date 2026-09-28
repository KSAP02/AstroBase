"""SQLite storage using the standard-library sqlite3 module (no ORM).

Two tables:
  rfqs         the RFQs, seeded from data_warehouse/seed/rfqs.json
  evaluations  one row per vendor evaluation (written from Step 4 onward)
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS rfqs (
    id        TEXT PRIMARY KEY,
    title     TEXT NOT NULL,
    category  TEXT NOT NULL,
    data      TEXT NOT NULL            -- the full RFQ as JSON
);

CREATE TABLE IF NOT EXISTS evaluations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rfq_id          TEXT NOT NULL REFERENCES rfqs(id),
    vendor_name     TEXT,
    vendor_text     TEXT NOT NULL,
    score           INTEGER NOT NULL,
    gate_passed     INTEGER NOT NULL,  -- 0 or 1
    result          TEXT NOT NULL,     -- JSON: verdicts, reasons, gaps, breakdown, raw LLM output
    model           TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    created_at      TEXT NOT NULL      -- UTC ISO-8601
);
"""


@contextmanager
def get_conn():
    """Open a connection, commit if the block succeeds, and always close it."""
    conn = sqlite3.connect(get_settings().db_file)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["title"]
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the DB file's folder and the tables if they don't exist yet."""
    get_settings().db_file.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def seed_rfqs(seed_file: Path | None = None) -> tuple[int, int]:
    """Insert the RFQs from rfqs.json. Safe to run repeatedly.

    Returns (inserted, already_present).
    """
    seed_file = seed_file or get_settings().seed_file
    rfqs = json.loads(seed_file.read_text(encoding="utf-8"))

    inserted = 0
    with get_conn() as conn:
        for rfq in rfqs:
            cur = conn.execute(
                # OR IGNORE: if this id already exists, skip it instead of raising an error.
                "INSERT OR IGNORE INTO rfqs (id, title, category, data) VALUES (?, ?, ?, ?)",
                (rfq["id"], rfq["title"], rfq["category"], json.dumps(rfq)),
            )
            inserted += cur.rowcount  # 1 if inserted, 0 if ignored
    return inserted, len(rfqs) - inserted


def list_rfqs() -> list[dict]:
    """Id, title and category of every RFQ, for the dropdown."""
    with get_conn() as conn:
        rows = conn.execute("SELECT id, title, category FROM rfqs ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def get_rfq(rfq_id: str) -> dict | None:
    """The full RFQ as a dict, or None if no RFQ has this id."""
    with get_conn() as conn:
        row = conn.execute("SELECT data FROM rfqs WHERE id = ?", (rfq_id,)).fetchone()
    return json.loads(row["data"]) if row else None
