"""Tabla de cuestionarios guardados.

Revision ID: 0001
Revises:
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "questionnaires",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("content", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questionnaires_created_at", "questionnaires", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_questionnaires_created_at", table_name="questionnaires")
    op.drop_table("questionnaires")
