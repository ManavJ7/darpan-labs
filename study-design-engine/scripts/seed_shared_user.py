#!/usr/bin/env python3
"""Seed the shared-login user and mark already-seeded studies public.

Idempotent — safe to run multiple times. On first run:
- Creates a `darpantry` user with the bcrypt-hashed password
- Flips `is_public = TRUE` on every existing study (so the seeded Dove
  demos surface on the anonymous landing page)

Subsequent runs only UPDATE the password hash (to support rotation) and
re-assert the public flag.

Usage:
    # Local
    python study-design-engine/scripts/seed_shared_user.py \\
        --username darpantry --password bezosisbad

    # Railway (after first deploy)
    railway run python study-design-engine/scripts/seed_shared_user.py \\
        --username darpantry --password "$SHARED_LOGIN_PASSWORD"

Env fallback: if --password is omitted, reads SHARED_LOGIN_PASSWORD. This lets
you avoid putting the password on the command line (shell history, ps output).
"""
import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

# Resolve project root so imports work whether run from repo root or subdir
SCRIPT_DIR = Path(__file__).resolve().parent
SDE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SDE_ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.auth_service import hash_password


async def seed(username: str, password: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    password_hash = hash_password(password)

    async with Session() as session:
        async with session.begin():
            # 1. Upsert the shared-login user.
            existing = await session.execute(
                text("SELECT id FROM users WHERE username = :u"), {"u": username}
            )
            row = existing.first()

            if row:
                user_id = row[0]
                await session.execute(
                    text("UPDATE users SET password_hash = :h WHERE id = :id"),
                    {"h": password_hash, "id": user_id},
                )
                print(f"[OK] Updated password for existing user '{username}' ({user_id})")
            else:
                user_id = uuid.uuid4()
                # Use raw SQL — the unified users table has more columns than
                # SDE's User model exposes (display_name, profile_completed, etc.)
                # so ORM insert would miss NOT NULL columns. Here we rely on
                # column defaults for everything we don't set explicitly.
                await session.execute(
                    text(
                        """
                        INSERT INTO users (id, email, username, password_hash, name, display_name)
                        VALUES (:id, :email, :username, :password_hash, :name, :display_name)
                        """
                    ),
                    {
                        "id": user_id,
                        "email": f"{username}@darpan-shared.local",
                        "username": username,
                        "password_hash": password_hash,
                        "name": username.capitalize(),
                        "display_name": username.capitalize(),
                    },
                )
                print(f"[OK] Created shared-login user '{username}' ({user_id})")

            # 2. Mark all currently-seeded studies as public.
            result = await session.execute(
                text("UPDATE studies SET is_public = TRUE WHERE is_public IS DISTINCT FROM TRUE RETURNING id")
            )
            updated = result.fetchall()
            if updated:
                print(f"[OK] Marked {len(updated)} studies as public")
                for r in updated:
                    print(f"     - {r[0]}")
            else:
                print("[OK] All studies already public (no changes)")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--username", required=True, help="Shared login username")
    parser.add_argument(
        "--password",
        default=os.environ.get("SHARED_LOGIN_PASSWORD"),
        help="Shared login password (or $SHARED_LOGIN_PASSWORD)",
    )
    args = parser.parse_args()

    if not args.password:
        parser.error("--password or $SHARED_LOGIN_PASSWORD is required")

    asyncio.run(seed(args.username, args.password))


if __name__ == "__main__":
    main()
