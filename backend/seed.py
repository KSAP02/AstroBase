"""Load the provided RFQs into SQLite.

Usage (from the repo root):  python -m backend.seed

Safe to re-run: RFQs that already exist are skipped. The API also does this
automatically on startup, so running it by hand is optional.
"""

from backend import db
from backend.config import get_settings


def main() -> None:
    db.init_db()
    inserted, skipped = db.seed_rfqs()
    print(f"Seeded {inserted} RFQs ({skipped} already present) into {get_settings().db_file}")


if __name__ == "__main__":
    main()
