"""add simulation_runs table

Revision ID: a1b2c3d4e5f6
Revises: 71b3ceacd3e0
Create Date: 2026-03-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '71b3ceacd3e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('simulation_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('study_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('inference_mode', sa.String(length=50), nullable=True),
        sa.Column('twin_count', sa.Integer(), nullable=True),
        sa.Column('question_count', sa.Integer(), nullable=True),
        sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['study_id'], ['studies.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('simulation_runs')
