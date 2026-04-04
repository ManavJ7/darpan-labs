"""Add twin pipeline tables: participants, digital_twins, pipeline_jobs,
pipeline_step_outputs, simulation_runs.

Revision ID: 002_twin_pipeline
Revises: b9718c989691
Create Date: 2026-04-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_twin_pipeline'
down_revision: Union[str, None] = 'b9718c989691'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- participants --
    op.create_table(
        'participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('external_id', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('profile_qa', postgresql.JSONB(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False, server_default='interview'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- digital_twins --
    op.create_table(
        'digital_twins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('participant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('participants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('twin_external_id', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('combo_id', sa.Integer(), nullable=True),
        sa.Column('coherence_score', sa.Float(), nullable=True),
        sa.Column('branch_choices', postgresql.JSONB(), nullable=True),
        sa.Column('profile_data', postgresql.JSONB(), nullable=False),
        sa.Column('profile_stats', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='building'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- pipeline_jobs --
    op.create_table(
        'pipeline_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_type', sa.String(30), nullable=False),
        sa.Column('participant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('participants.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('study_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('current_step', sa.String(30), nullable=True),
        sa.Column('progress', postgresql.JSONB(), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('result_summary', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('celery_task_id', sa.String(255), nullable=True, index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    # -- pipeline_step_outputs --
    op.create_table(
        'pipeline_step_outputs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('participant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('participants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pipeline_jobs.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('step_name', sa.String(30), nullable=False),
        sa.Column('mode', sa.String(20), nullable=False, server_default='1to1'),
        sa.Column('output_data', postgresql.JSONB(), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('participant_id', 'step_name', 'mode', name='uq_step_output_per_participant'),
    )

    # -- validation_reports --
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

    # -- simulation_runs --
    op.create_table(
        'simulation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pipeline_jobs.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('twin_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('digital_twins.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('study_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('questionnaire_snapshot', postgresql.JSONB(), nullable=False),
        sa.Column('inference_mode', sa.String(20), nullable=False, server_default='combined'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('responses', postgresql.JSONB(), nullable=True),
        sa.Column('summary_stats', postgresql.JSONB(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('simulation_runs')
    op.drop_table('validation_reports')
    op.drop_table('pipeline_step_outputs')
    op.drop_table('pipeline_jobs')
    op.drop_table('digital_twins')
    op.drop_table('participants')
