"""add_public_studies_and_password_auth

Revision ID: e5f6a7b8c9d0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-18 00:00:00.000000

Two schema changes for the /try deploy:

1. `studies.is_public` — frozen-demo flag; public studies are readable by any
   visitor (authenticated or not) and writable by no one. Used to surface the
   seeded Dove studies on the landing page without requiring login.
2. `users.username` + `users.password_hash` — enables a shared-login account
   (darpantry) alongside the existing Google OAuth path. `google_sub` becomes
   nullable so password-only users can exist.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # studies.is_public
    op.add_column(
        "studies",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_studies_is_public", "studies", ["is_public"])

    # users.username + users.password_hash, relax users.google_sub
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_index("ix_users_username", "users", ["username"])
    op.alter_column(
        "users",
        "google_sub",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "google_sub",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.drop_index("ix_users_username", table_name="users")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")

    op.drop_index("ix_studies_is_public", table_name="studies")
    op.drop_column("studies", "is_public")
