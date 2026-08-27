"""Add analyzing_findings value to scanstage enum.

The Python ScanStage enum gained ANALYZING_FINDINGS for the decoupled
scan/AI pipeline, but PostgreSQL rejects unknown enum labels until migrated.

Revision ID: 038
Revises: 037
Create Date: 2026-08-26
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision = "038"
down_revision = "037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL 9.1+ supports ALTER TYPE ... ADD VALUE.
    # IF NOT EXISTS is available on PG 15+; use a guarded statement for idempotency.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'scanstage'
                  AND e.enumlabel = 'analyzing_findings'
            ) THEN
                ALTER TYPE scanstage ADD VALUE 'analyzing_findings';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL cannot drop individual enum values safely; leave scanstage unchanged.
    pass
