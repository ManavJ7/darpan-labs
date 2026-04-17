"""add_study_ownership

Revision ID: c4d5e6f7a8b9
Revises: 2bc40327f7cc
Create Date: 2026-04-13 04:50:00.000000

Adds `created_by_user_id` FK to `studies`. Nullable so existing rows survive
the migration — they get claimed on first authenticated mutation via
`require_study_owner` in app/auth.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = '2bc40327f7cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "studies",
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_studies_created_by_user_id",
        "studies",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_studies_created_by_user_id",
        "studies",
        ["created_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_studies_created_by_user_id", table_name="studies")
    op.drop_constraint("fk_studies_created_by_user_id", "studies", type_="foreignkey")
    op.drop_column("studies", "created_by_user_id")
