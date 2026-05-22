"""initial schema

Revision ID: 202605220001
Revises:
Create Date: 2026-05-22 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605220001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=False)

    op.create_table(
        "test_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=100), nullable=True),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("accuracy_percent", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_attempts_user_id"), "test_attempts", ["user_id"], unique=False)

    op.create_table(
        "answer_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(length=100), nullable=False),
        sa.Column("selected_index", sa.Integer(), nullable=False),
        sa.Column("correct_index", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("subject", sa.String(length=100), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("subtopic", sa.String(length=255), nullable=True),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["test_attempts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_answer_results_attempt_id"), "answer_results", ["attempt_id"], unique=False)
    op.create_index(op.f("ix_answer_results_question_id"), "answer_results", ["question_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_answer_results_question_id"), table_name="answer_results")
    op.drop_index(op.f("ix_answer_results_attempt_id"), table_name="answer_results")
    op.drop_table("answer_results")
    op.drop_index(op.f("ix_test_attempts_user_id"), table_name="test_attempts")
    op.drop_table("test_attempts")
    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_table("users")
