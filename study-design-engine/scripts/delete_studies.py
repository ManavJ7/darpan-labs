#!/usr/bin/env python3
"""Delete one or more studies from the SDE database along with all dependent rows.

Context
-------
`DELETE FROM studies WHERE id = ...` fails because 5 child tables FK to `studies.id`
with `NO ACTION` cascade rules: `step_versions`, `concepts`, `simulation_runs`,
`review_comments`, `audit_log`. Two more tables (`pipeline_jobs`, `validation_reports`)
reference `study_id` without a formal FK — cleaning them up keeps orphaned rows
from piling up. This script does all of that inside a single transaction so the
delete is atomic.

Usage
-----
  # Dry-run: show what would be deleted, no DB writes
  python3 scripts/delete_studies.py <uuid_or_substring> [<uuid_or_substring> ...]

  # Actually delete (required)
  python3 scripts/delete_studies.py <id...> --confirm

  # Protection: refuses to delete any study whose status is 'complete' unless
  # --force is also passed. Completed studies have simulation results that are
  # expensive to reproduce.
  python3 scripts/delete_studies.py <id> --confirm --force

Each argument can be either:
  * a full UUID (`17c7ea0e-6a5d-48ad-8c3b-950ac7f58e5e`)
  * a UUID prefix (`17c7ea0e`)
  * a case-insensitive substring that matches `question` or `title`
    (`"ad ideas"` → matches any study whose question contains that phrase)

Connection
----------
Reads `DATABASE_URL` from the environment. Falls back to the local default
(`postgresql://manavrsjain@localhost:5432/darpan`) if unset — matches the SDE
backend's default config so the script "just works" in dev.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


# Child tables that must be purged before the study row can be deleted. Order
# matters only where there are inter-child FKs; we delete in a single
# transaction so any ordering issue would surface as a clear FK error.
CHILD_TABLES: list[str] = [
    "simulation_runs",       # FK → studies (NO ACTION), FK → pipeline_jobs (SET NULL)
    "validation_reports",    # FK → pipeline_jobs (SET NULL); has study_id col
    "audit_log",             # FK → studies (NO ACTION)
    "concepts",               # FK → studies (NO ACTION)
    "review_comments",       # FK → studies (NO ACTION)
    "step_versions",         # FK → studies (NO ACTION)
    "pipeline_jobs",          # study_id column, no formal FK
]


def _default_dsn() -> str:
    """Normalize `DATABASE_URL` into a psycopg2-compatible DSN.

    The SDE uses the async SQLAlchemy driver prefix `postgresql+asyncpg://`,
    which psycopg2 doesn't understand. Strip the `+asyncpg` subdialect if
    present so the same env var works for this sync script.
    """
    raw = os.environ.get("DATABASE_URL", "postgresql://manavrsjain@localhost:5432/darpan")
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def resolve_targets(
    conn,
    selectors: list[str],
) -> list[dict]:
    """Turn user-supplied selectors (UUIDs, UUID prefixes, substrings) into
    a deduplicated list of matching study rows.

    Returns the full study records so the caller can show context before
    deleting and enforce the `--force` guard on completed studies.
    """
    sql = """
        SELECT id, COALESCE(NULLIF(title, ''), LEFT(question, 80)) AS label,
               status, created_at
        FROM studies
        WHERE {clause}
    """
    found: dict[str, dict] = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for sel in selectors:
            sel = sel.strip()
            if not sel:
                continue
            # UUID-ish (36 chars with dashes, or >= 8-char prefix)
            if len(sel) >= 8 and all(c in "0123456789abcdef-" for c in sel.lower()):
                cur.execute(sql.format(clause="id::text LIKE %s"), (f"{sel.lower()}%",))
            else:
                pattern = f"%{sel}%"
                cur.execute(
                    sql.format(clause="question ILIKE %s OR title ILIKE %s"),
                    (pattern, pattern),
                )
            for row in cur.fetchall():
                found[str(row["id"])] = row
    return sorted(found.values(), key=lambda r: r["created_at"] or "")


def preview_counts(conn, study_ids: list[str]) -> list[tuple[str, int]]:
    """Return (table, rows_that_will_be_deleted) for each child table."""
    counts: list[tuple[str, int]] = []
    with conn.cursor() as cur:
        for table in CHILD_TABLES:
            cur.execute(
                f"SELECT COUNT(*) FROM {table} WHERE study_id = ANY(%s::uuid[])",
                (study_ids,),
            )
            counts.append((table, cur.fetchone()[0]))
    return counts


def execute_delete(conn, study_ids: list[str]) -> dict[str, int]:
    """Delete children then the study rows. Caller wraps in a transaction."""
    deleted: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in CHILD_TABLES:
            cur.execute(
                f"DELETE FROM {table} WHERE study_id = ANY(%s::uuid[])",
                (study_ids,),
            )
            deleted[table] = cur.rowcount
        cur.execute(
            "DELETE FROM studies WHERE id = ANY(%s::uuid[])",
            (study_ids,),
        )
        deleted["studies"] = cur.rowcount
    return deleted


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Delete studies + dependent rows from the SDE database.",
        epilog="Without --confirm this runs as a dry-run and shows what would be deleted.",
    )
    parser.add_argument(
        "selectors",
        nargs="+",
        help="Study IDs, UUID prefixes, or question/title substrings.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually perform the deletion. Default is dry-run.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow deletion of studies whose status is 'complete'. Dangerous: "
             "these have simulation results that cost real money to regenerate.",
    )
    parser.add_argument(
        "--dsn",
        default=None,
        help="Override DATABASE_URL. Accepts psycopg2-style DSN.",
    )
    args = parser.parse_args(argv)

    dsn = args.dsn or _default_dsn()
    conn = psycopg2.connect(dsn)
    conn.autocommit = False

    try:
        targets = resolve_targets(conn, args.selectors)
        if not targets:
            print("No studies matched your selectors. Nothing to do.")
            return 1

        # Guard: completed studies require --force
        completed = [t for t in targets if t["status"] == "complete"]
        if completed and not args.force:
            print("Refusing to delete the following COMPLETED studies without --force:")
            for t in completed:
                print(f"  [COMPLETE]  {t['id']}  {t['label']}")
            print("  (Their simulations cost real LLM spend to reproduce.)")
            print("  Pass --force to override, or remove their IDs from the selectors.")
            return 2

        study_ids = [str(t["id"]) for t in targets]

        print(f"\nMatched {len(targets)} study(ies):")
        for t in targets:
            print(f"  {t['id']}  [{t['status']:<14}]  {t['label']}")

        counts = preview_counts(conn, study_ids)
        total_children = sum(n for _, n in counts)
        print(f"\nDependent rows that will be deleted ({total_children} total):")
        for table, n in counts:
            flag = "" if n == 0 else "  <-- non-empty"
            print(f"  {table:<22}  {n} row(s){flag}")

        if not args.confirm:
            print("\nDRY RUN — no changes made. Pass --confirm to actually delete.")
            return 0

        deleted = execute_delete(conn, study_ids)
        conn.commit()

        print("\nDELETED:")
        for table, n in deleted.items():
            print(f"  {table:<22}  {n} row(s)")
        print(f"\nSUCCESS — {deleted['studies']} study(ies) purged.")
        return 0

    except Exception as exc:
        conn.rollback()
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("Transaction rolled back — no changes made.", file=sys.stderr)
        return 3
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
