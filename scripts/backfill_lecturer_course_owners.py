#!/usr/bin/env python3
"""One-time backfill: assign lecturer_id to catalog courses by department match."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "agency" / ".env", override=False)

from agency.core.tools.database import Database
from fastapi_app.bootstrap import init_database
from fastapi_app.services.lecturer_backfill_service import backfill_lecturer_ids_by_department


def main() -> None:
    init_database()
    db = Database()
    with db._SessionLocal() as session:  # noqa: SLF001
        result = backfill_lecturer_ids_by_department(session)
    print(f"Assigned: {result['assigned']}, Skipped: {result['skipped']}")
    for row in result.get("details", [])[:20]:
        print(row)


if __name__ == "__main__":
    main()
