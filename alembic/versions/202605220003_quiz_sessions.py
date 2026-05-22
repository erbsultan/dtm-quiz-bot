"""quiz sessions

Revision ID: 202605220003
Revises: 202605220002
Create Date: 2026-05-22 00:03:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605220003"
down_revision: str | None = "202605220002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quiz_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("language_code", sa.String(length=5), server_default="uz", nullable=False),
        sa.Column("exam_profile_code", sa.String(length=50), nullable=True),
        sa.Column("current_question_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("question_ids", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quiz_sessions_status"), "quiz_sessions", ["status"], unique=False)
    op.create_index(op.f("ix_quiz_sessions_user_id"), "quiz_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_quiz_sessions_user_id"), table_name="quiz_sessions")
    op.drop_index(op.f("ix_quiz_sessions_status"), table_name="quiz_sessions")
    op.drop_table("quiz_sessions")
