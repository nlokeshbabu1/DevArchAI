"""Add token_family column to user_sessions for refresh token reuse detection.

Each new refresh token is assigned a family identifier (UUID).  When a
refresh request arrives the backend checks that the token's family has not
been seen before; if it has, the entire session/family is revoked because
it indicates a stolen token.

Revision ID: 036
Revises: 035
Create Date: 2026-08-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "036"
down_revision = "035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_sessions",
        sa.Column("token_family", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_user_sessions_token_family",
        "user_sessions",
        ["token_family"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_sessions_token_family", table_name="user_sessions")
    op.drop_column("user_sessions", "token_family")
