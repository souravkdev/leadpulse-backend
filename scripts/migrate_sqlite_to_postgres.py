"""One-time SQLite -> PostgreSQL data migration for LeadPulse.

Usage:
  python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-url sqlite:///./leadpulse.db \
    --postgres-url postgresql+psycopg2://postgres:postgres@localhost:5432/leadpulse
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

TABLE_ORDER = ["users", "leads", "activities"]


@dataclass
class MigrationStats:
    table: str
    source_count: int
    inserted_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate LeadPulse data from SQLite to PostgreSQL")
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
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Truncate target tables before insert",
    )
    return parser.parse_args()


def fetch_rows(engine: Engine, table: str) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {table}"))
        return [dict(row._mapping) for row in result]


def normalize_rows_for_postgres(table: str, rows: list[dict]) -> list[dict]:
    if not rows:
        return rows

    normalized: list[dict] = []
    for row in rows:
        new_row = dict(row)

        # SQLite persists booleans as 0/1 integers, but PostgreSQL expects true/false.
        if table == "users" and "is_active" in new_row and new_row["is_active"] is not None:
            new_row["is_active"] = bool(new_row["is_active"])

        normalized.append(new_row)

    return normalized


def truncate_tables(engine: Engine) -> None:
    # Reverse order for FK-safe truncation.
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE activities, leads, users RESTART IDENTITY CASCADE"))


def insert_rows(engine: Engine, table: str, rows: list[dict]) -> int:
    if not rows:
        return 0

    columns = list(rows[0].keys())
    col_names = ", ".join(columns)
    bind_names = ", ".join(f":{c}" for c in columns)

    statement = text(f"INSERT INTO {table} ({col_names}) VALUES ({bind_names})")

    with engine.begin() as conn:
        conn.execute(statement, rows)

    return len(rows)


def ensure_target_tables_exist(engine: Engine) -> None:
    check_sql = text(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = :table_name
        """
    )

    with engine.connect() as conn:
        for table in TABLE_ORDER:
            exists = conn.execute(check_sql, {"table_name": table}).first()
            if not exists:
                raise RuntimeError(
                    f"Target table '{table}' not found. Run Alembic migrations on PostgreSQL first."
                )


def run_migration(sqlite_url: str, postgres_url: str, truncate_target: bool) -> list[MigrationStats]:
    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(postgres_url)

    ensure_target_tables_exist(postgres_engine)

    if truncate_target:
        truncate_tables(postgres_engine)

    stats: list[MigrationStats] = []

    for table in TABLE_ORDER:
        rows = fetch_rows(sqlite_engine, table)
        rows = normalize_rows_for_postgres(table, rows)
        inserted = insert_rows(postgres_engine, table, rows)
        stats.append(MigrationStats(table=table, source_count=len(rows), inserted_count=inserted))

    return stats


def main() -> None:
    args = parse_args()

    stats = run_migration(
        sqlite_url=args.sqlite_url,
        postgres_url=args.postgres_url,
        truncate_target=args.truncate_target,
    )

    print("Migration completed.")
    for item in stats:
        print(
            f"- {item.table}: source_rows={item.source_count}, inserted_rows={item.inserted_count}"
        )


if __name__ == "__main__":
    main()
