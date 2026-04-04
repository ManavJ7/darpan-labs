"""Initial migration - create all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-02-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('auth_provider_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create consent_events table
    op.create_table(
        'consent_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('consent_type', sa.String(50), nullable=False),
        sa.Column('consent_version', sa.String(20), nullable=False),
        sa.Column('accepted', sa.Boolean(), nullable=False),
        sa.Column('consent_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create interview_sessions table
    op.create_table(
        'interview_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('input_mode', sa.String(20), nullable=False, default='text'),
        sa.Column('language_preference', sa.String(10), nullable=False, default='auto'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_duration_sec', sa.Integer(), nullable=True),
        sa.Column('settings', postgresql.JSONB(), nullable=True),
    )

    # Create interview_modules table
    op.create_table(
        'interview_modules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('module_id', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('question_count', sa.Integer(), nullable=False, default=0),
        sa.Column('coverage_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('confidence_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('signals_captured', postgresql.JSONB(), nullable=True),
        sa.Column('completion_eval', postgresql.JSONB(), nullable=True),
    )

    # Create interview_turns table
    op.create_table(
        'interview_turns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('module_id', sa.String(10), nullable=False),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('input_mode', sa.String(20), nullable=False, default='text'),
        sa.Column('question_text', sa.Text(), nullable=True),
        sa.Column('question_meta', postgresql.JSONB(), nullable=True),
        sa.Column('answer_text', sa.Text(), nullable=True),
        sa.Column('answer_raw_transcript', sa.Text(), nullable=True),
        sa.Column('answer_language', sa.String(10), nullable=True),
        sa.Column('answer_structured', postgresql.JSONB(), nullable=True),
        sa.Column('answer_meta', postgresql.JSONB(), nullable=True),
        sa.Column('audio_meta', postgresql.JSONB(), nullable=True),
        sa.Column('audio_storage_ref', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create twin_profiles table
    op.create_table(
        'twin_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('status', sa.String(20), nullable=False, default='generating'),
        sa.Column('modules_included', postgresql.ARRAY(sa.String(10)), nullable=False),
        sa.Column('quality_label', sa.String(20), nullable=False, default='base'),
        sa.Column('quality_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('structured_profile_json', postgresql.JSONB(), nullable=True),
        sa.Column('persona_summary_text', sa.Text(), nullable=True),
        sa.Column('persona_full_text', sa.Text(), nullable=True),
        sa.Column('coverage_confidence', postgresql.JSONB(), nullable=True),
        sa.Column('extraction_meta', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create evidence_snippets table
    op.create_table(
        'evidence_snippets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('twin_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('twin_profiles.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('module_id', sa.String(10), nullable=False),
        sa.Column('turn_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_turns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snippet_text', sa.Text(), nullable=False),
        sa.Column('snippet_category', sa.String(50), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('snippet_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create twin_chat_sessions table
    op.create_table(
        'twin_chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('twin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('twin_profiles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create twin_chat_messages table
    op.create_table(
        'twin_chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('twin_chat_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('confidence_label', sa.String(20), nullable=True),
        sa.Column('evidence_used', postgresql.JSONB(), nullable=True),
        sa.Column('coverage_gaps', postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column('model_meta', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create cohorts table
    op.create_table(
        'cohorts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('twin_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column('filters_used', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create experiments table
    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('cohort_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cohorts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('scenario', postgresql.JSONB(), nullable=False),
        sa.Column('settings', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('aggregate_results', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create experiment_results table
    op.create_table(
        'experiment_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('twin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('twin_profiles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('choice', sa.String(255), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('confidence_label', sa.String(20), nullable=False),
        sa.Column('evidence_used', postgresql.JSONB(), nullable=True),
        sa.Column('coverage_gaps', postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column('model_meta', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('experiment_results')
    op.drop_table('experiments')
    op.drop_table('cohorts')
    op.drop_table('twin_chat_messages')
    op.drop_table('twin_chat_sessions')
    op.drop_table('evidence_snippets')
    op.drop_table('twin_profiles')
    op.drop_table('interview_turns')
    op.drop_table('interview_modules')
    op.drop_table('interview_sessions')
    op.drop_table('consent_events')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS vector')
