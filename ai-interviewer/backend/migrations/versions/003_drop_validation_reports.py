"""drop validation_reports table

Revision ID: 003_drop_validation_reports
Revises: 002_twin_pipeline
Create Date: 2026-04-26 00:00:00.000000

Mirror of the SDE drop migration. The validation_reports table was created
by 002_add_twin_pipeline_tables but is no longer used. Drop it idempotently
(IF EXISTS handles the case where the SDE chain already dropped it on the
shared DB). Downgrade recreates the original column shape.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '003_drop_validation_reports'
down_revision: Union[str, None] = '002_twin_pipeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS validation_reports CASCADE")


def downgrade() -> None:
    op.create_table(
        'validation_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('study_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pipeline_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('twin_count', sa.Integer(), nullable=True),
        sa.Column('real_count', sa.Integer(), nullable=True),
        sa.Column('report_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
