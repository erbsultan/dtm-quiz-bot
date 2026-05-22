"""stage 2 language and scoring

Revision ID: 202605220002
Revises: 202605220001
Create Date: 2026-05-22 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605220002"
down_revision: str | None = "202605220001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("language_code", sa.String(length=5), server_default="uz", nullable=False),
    )
    op.add_column("users", sa.Column("exam_profile_code", sa.String(length=50), nullable=True))

    op.add_column(
        "test_attempts",
        sa.Column("score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "test_attempts",
        sa.Column("max_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "test_attempts",
        sa.Column("score_percent", sa.Float(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("test_attempts", "score_percent")
    op.drop_column("test_attempts", "max_score")
    op.drop_column("test_attempts", "score")
    op.drop_column("users", "exam_profile_code")
    op.drop_column("users", "language_code")
