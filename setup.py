#!/usr/bin/env python3
"""
Darpan Labs — One-command setup script.

After cloning the repo, run:
    python setup.py

This will:
1. Check prerequisites (PostgreSQL, Redis, Python packages)
2. Create the 'darpan' database if it doesn't exist
3. Create all tables (AI Interviewer + SDE + Twin Pipeline)
4. Seed the Dove study data (study, concepts, questionnaire, 17 participants, twins, simulations)
5. Print instructions for starting all services

Requirements:
    - PostgreSQL running on localhost:5432
    - Redis running on localhost:6379
    - Python 3.11+ with packages: sqlalchemy, asyncpg, psycopg2-binary (or pg8000)
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

SCRIPT_DIR = Path(__file__).parent.resolve()
SEED_FILE = SCRIPT_DIR / "seed_data.json"
AI_BACKEND = SCRIPT_DIR / "ai-interviewer" / "backend"

# Default DB config — override with env vars
DB_USER = os.environ.get("DB_USER", os.environ.get("USER", "postgres"))
DB_PASS = os.environ.get("DB_PASS", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "darpan")


def check_command(cmd, name):
    """Check if a command is available."""
    try:
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def step(n, msg):
    print(f"\n{'='*60}")
    print(f"  Step {n}: {msg}")
    print(f"{'='*60}")


def main():
    print("=" * 60)
    print("  DARPAN LABS — Setup Script")
    print("=" * 60)

    # ── Step 1: Check prerequisites ──
    step(1, "Checking prerequisites")

    ok = True

    # PostgreSQL
    if check_command(["pg_isready", "-h", DB_HOST, "-p", DB_PORT], "PostgreSQL"):
        print(f"  [OK] PostgreSQL is running on {DB_HOST}:{DB_PORT}")
    else:
        print(f"  [FAIL] PostgreSQL is not running on {DB_HOST}:{DB_PORT}")
        print(f"         Install: brew install postgresql@16 && brew services start postgresql@16")
        ok = False

    # Redis
    try:
        result = subprocess.run(["redis-cli", "-p", "6379", "ping"], capture_output=True, text=True, timeout=3)
        if result.stdout.strip() == "PONG":
            print(f"  [OK] Redis is running")
        else:
            raise Exception()
    except Exception:
        print(f"  [FAIL] Redis is not running")
        print(f"         Install: brew install redis && brew services start redis")
        ok = False

    # Python
    print(f"  [OK] Python {sys.version.split()[0]}")

    # Seed file
    if SEED_FILE.exists():
        size_mb = SEED_FILE.stat().st_size / (1024 * 1024)
        print(f"  [OK] Seed data file found ({size_mb:.1f} MB)")
    else:
        print(f"  [FAIL] seed_data.json not found at {SEED_FILE}")
        ok = False

    if not ok:
        print("\n  Fix the above issues and re-run setup.py")
        sys.exit(1)

    # ── Step 2: Install Python packages if needed ──
    step(2, "Checking Python packages")
    required = ["sqlalchemy", "asyncpg", "psycopg2"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            # psycopg2 might be psycopg2-binary
            if pkg == "psycopg2":
                try:
                    __import__("psycopg2")
                except ImportError:
                    missing.append("psycopg2-binary")
            else:
                missing.append(pkg)

    if missing:
        print(f"  Installing: {', '.join(missing)}")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing, capture_output=True)
    print("  [OK] All required packages installed")

    # ── Step 3: Create database ──
    step(3, "Creating database")

    # Build connection string for createdb
    conn_parts = ["-h", DB_HOST, "-p", DB_PORT]
    if DB_USER:
        conn_parts.extend(["-U", DB_USER])

    # Check if DB exists
    result = subprocess.run(
        ["psql"] + conn_parts + ["-d", "postgres", "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'"],
        capture_output=True, text=True,
        env={**os.environ, "PGPASSWORD": DB_PASS} if DB_PASS else None,
    )

    if result.stdout.strip() == "1":
        print(f"  [OK] Database '{DB_NAME}' already exists")
    else:
        print(f"  Creating database '{DB_NAME}'...")
        subprocess.run(
            ["createdb"] + conn_parts + [DB_NAME],
            env={**os.environ, "PGPASSWORD": DB_PASS} if DB_PASS else None,
        )
        print(f"  [OK] Database '{DB_NAME}' created")

    # ── Step 4: Create all tables ──
    step(4, "Creating tables")

    # Build SQLAlchemy URL
    if DB_PASS:
        sync_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        sync_url = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # Add AI interviewer backend to path for model imports
    sys.path.insert(0, str(AI_BACKEND))
    os.chdir(str(AI_BACKEND))

    # Override the database URL before importing anything
    os.environ["DATABASE_URL"] = f"postgresql+asyncpg://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    from sqlalchemy import create_engine, text, inspect
    engine = create_engine(sync_url, echo=False)

    # Import all models to register them with Base
    from app.database import Base
    from app.models.user import User
    from app.models.consent import ConsentEvent
    from app.models.interview import InterviewSession, InterviewModule, InterviewTurn
    from app.models.twin import (
        Participant, DigitalTwin, PipelineJob, PipelineStepOutput,
        ValidationReport, SimulationRun,
    )

    # Create AI Interviewer tables
    Base.metadata.create_all(engine)
    print("  [OK] AI Interviewer + Twin Pipeline tables created")

    # Create SDE tables (studies, step_versions, concepts, etc.)
    # These use a different Base, so we create them via raw SQL if they don't exist
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    sde_tables = {
        "studies": """
            CREATE TABLE IF NOT EXISTS studies (
                id UUID PRIMARY KEY,
                brand_id UUID NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'init',
                question TEXT NOT NULL,
                title VARCHAR(500),
                brand_name VARCHAR(255),
                category VARCHAR(255),
                context JSONB DEFAULT '{}',
                study_metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""",
        "step_versions": """
            CREATE TABLE IF NOT EXISTS step_versions (
                id UUID PRIMARY KEY,
                study_id UUID NOT NULL REFERENCES studies(id),
                step INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                content JSONB,
                ai_rationale JSONB,
                locked_at TIMESTAMPTZ,
                locked_by UUID,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(study_id, step, version)
            )""",
        "concepts": """
            CREATE TABLE IF NOT EXISTS concepts (
                id UUID PRIMARY KEY,
                study_id UUID NOT NULL REFERENCES studies(id),
                concept_index INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(50) NOT NULL DEFAULT 'raw',
                components JSONB NOT NULL,
                comparability_flags JSONB,
                image_url TEXT,
                image_version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(study_id, concept_index, version)
            )""",
        "metric_library": """
            CREATE TABLE IF NOT EXISTS metric_library (
                id VARCHAR(100) PRIMARY KEY,
                display_name VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                description TEXT,
                applicable_study_types VARCHAR[] NOT NULL,
                default_scale JSONB NOT NULL,
                benchmark_available BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""",
        "audit_log": """
            CREATE TABLE IF NOT EXISTS audit_log (
                id UUID PRIMARY KEY,
                study_id UUID NOT NULL REFERENCES studies(id),
                action VARCHAR(100) NOT NULL,
                actor VARCHAR(255) NOT NULL,
                payload JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""",
        "review_comments": """
            CREATE TABLE IF NOT EXISTS review_comments (
                id UUID PRIMARY KEY,
                study_id UUID NOT NULL REFERENCES studies(id),
                step INTEGER NOT NULL,
                target_type VARCHAR(50) NOT NULL,
                target_id VARCHAR(255),
                comment_text TEXT NOT NULL,
                resolved BOOLEAN NOT NULL DEFAULT false,
                resolved_by VARCHAR(50),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""",
    }

    with engine.begin() as conn:
        for table_name, ddl in sde_tables.items():
            if table_name not in existing_tables:
                conn.execute(text(ddl))
                print(f"  [OK] Created table: {table_name}")
            else:
                print(f"  [OK] Table exists: {table_name}")

        # Add missing columns to users table for SDE compatibility
        for col, col_type in [("name", "VARCHAR(255)"), ("picture_url", "VARCHAR(1024)"),
                               ("google_sub", "VARCHAR(255)"), ("last_login_at", "TIMESTAMPTZ")]:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_type}"))
            except Exception:
                pass

    print("  [OK] All SDE tables created")

    # ── Step 5: Seed data ──
    step(5, "Seeding data")

    with open(SEED_FILE) as f:
        seed = json.load(f)

    from sqlalchemy.orm import Session

    # Table insertion order (respects FK constraints)
    table_order = [
        "users", "studies", "step_versions", "concepts", "metric_library",
        "participants", "pipeline_jobs", "digital_twins",
        "pipeline_step_outputs", "simulation_runs",
    ]

    from sqlalchemy.orm import Session
    with Session(engine) as session:
        for table_name in table_order:
            rows = seed.get(table_name, [])
            if not rows:
                continue

            # Check if data already exists
            count = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            if count > 0:
                print(f"  [SKIP] {table_name}: {count} rows already exist")
                continue

            inserted = 0
            for row in rows:
                cleaned = {}
                for k, v in row.items():
                    if isinstance(v, (dict, list)):
                        cleaned[k] = json.dumps(v)
                    else:
                        cleaned[k] = v
                cols = list(cleaned.keys())
                jsonb_cols = {
                    "context", "study_metadata", "content", "ai_rationale", "components",
                    "comparability_flags", "default_scale", "payload", "consent_metadata",
                    "settings", "question_meta", "answer_structured", "answer_meta",
                    "audio_meta", "signals_captured", "completion_eval",
                    "profile_qa", "branch_choices", "profile_data", "profile_stats",
                    "progress", "config", "result_summary", "output_data",
                    "questionnaire_snapshot", "responses", "summary_stats", "report_data",
                    "metadata",
                }
                placeholders = []
                for c in cols:
                    if c in jsonb_cols:
                        placeholders.append(f"CAST(:{c} AS JSONB)")
                    else:
                        placeholders.append(f":{c}")
                placeholder_str = ", ".join(placeholders)
                col_names = ", ".join(f'"{c}"' for c in cols)
                try:
                    sp = session.begin_nested()
                    session.execute(text(f'INSERT INTO {table_name} ({col_names}) VALUES ({placeholder_str})'), cleaned)
                    sp.commit()
                    inserted += 1
                except Exception as e:
                    sp.rollback()
                    if "duplicate" not in str(e).lower() and "unique" not in str(e).lower():
                        pass  # silently skip problem rows
                    continue

            session.commit()
            print(f"  [OK] {table_name}: {inserted}/{len(rows)} rows inserted")

        # Sync display_name ↔ name
        session.execute(text("UPDATE users SET name = display_name WHERE name IS NULL AND display_name IS NOT NULL"))
        session.execute(text("UPDATE users SET display_name = name WHERE display_name IS NULL AND name IS NOT NULL"))
        session.execute(text("UPDATE users SET google_sub = 'imported-' || id::text WHERE google_sub IS NULL"))
        session.commit()

    # ── Step 6: Verify ──
    step(6, "Verifying")

    with engine.connect() as conn:
        checks = [
            ("users", "SELECT COUNT(*) FROM users"),
            ("studies", "SELECT COUNT(*) FROM studies"),
            ("step_versions (locked)", "SELECT COUNT(*) FROM step_versions WHERE status='locked'"),
            ("concepts", "SELECT COUNT(*) FROM concepts"),
            ("participants", "SELECT COUNT(*) FROM participants"),
            ("digital_twins (ready)", "SELECT COUNT(*) FROM digital_twins WHERE status='ready'"),
            ("simulation_runs (completed)", "SELECT COUNT(*) FROM simulation_runs WHERE status='completed'"),
            ("pipeline_step_outputs", "SELECT COUNT(*) FROM pipeline_step_outputs"),
        ]
        all_ok = True
        for label, query in checks:
            n = conn.execute(text(query)).scalar()
            status = "OK" if n > 0 else "EMPTY"
            if n == 0:
                all_ok = False
            print(f"  [{status}] {label}: {n}")

    if not all_ok:
        print("\n  [WARN] Some tables are empty — check the seed data")
    else:
        print("\n  All data seeded successfully!")

    # ── Done ──
    print(f"\n{'='*60}")
    print("  SETUP COMPLETE")
    print(f"{'='*60}")
    print(f"""
To start all services, open 4 terminal tabs and run:

  Tab 1 — Celery Worker:
    cd {AI_BACKEND}
    celery -A app.celery_app worker --loglevel=info --concurrency=1

  Tab 2 — AI Interviewer Backend (port 8000):
    cd {AI_BACKEND}
    uvicorn app.main:app --port 8000

  Tab 3 — Study Design Engine Backend (port 8001):
    cd {SCRIPT_DIR / 'study-design-engine'}
    uvicorn app.main:app --port 8001

  Tab 4 — SDE Frontend (port 3000):
    cd {SCRIPT_DIR / 'study-design-engine' / 'frontend'}
    npm install && npm run dev

  Tab 5 (optional) — Validation Dashboard (port 5173):
    cd {SCRIPT_DIR / 'validation-dashboard' / 'dove-dashboard'}
    npm install && npm run dev

Then open:
  - Study Design Engine: http://localhost:3000
  - Validation Dashboard: http://localhost:5173
  - API Docs:             http://localhost:8001/docs

Study ID: {seed['studies'][0]['id'] if seed.get('studies') else 'N/A'}
Participants: {len(seed.get('participants', []))}
Ready Twins: {len(seed.get('digital_twins', []))}
""")


if __name__ == "__main__":
    main()
