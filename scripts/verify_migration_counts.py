"""Verify SQLite -> PostgreSQL row counts for LeadPulse core tables.

Usage:
  python scripts/verify_migration_counts.py \
    --sqlite-url sqlite:///./leadpulse.db \
    --postgres-url postgresql+psycopg2://postgres:postgres@localhost:5432/leadpulse
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

TABLES = ["users", "leads", "activities"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare SQLite and PostgreSQL row counts for migration validation"
    )
    parser.add_argument(
        "--sqlite-url",
        default="sqlite:///./leadpulse.db",
        help="Source SQLite URL",
    )
    parser.add_argument(
        "--postgres-url",
        required=True,
        help="Target PostgreSQL URL",
    )
    return parser.parse_args()


def table_count(engine: Engine, table_name: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())


def main() -> None:
    args = parse_args()

    sqlite_engine = create_engine(args.sqlite_url)
    postgres_engine = create_engine(args.postgres_url)

    has_mismatch = False

    print("Migration count verification:")
    for table_name in TABLES:
        sqlite_count = table_count(sqlite_engine, table_name)
        postgres_count = table_count(postgres_engine, table_name)
        status = "OK" if sqlite_count == postgres_count else "MISMATCH"
        print(
            f"- {table_name}: sqlite={sqlite_count}, postgres={postgres_count}, status={status}"
        )
        if sqlite_count != postgres_count:
            has_mismatch = True

    if has_mismatch:
        print("Verification failed: one or more table counts do not match.")
        sys.exit(1)

    print("Verification passed: all table counts match.")


if __name__ == "__main__":
    main()
