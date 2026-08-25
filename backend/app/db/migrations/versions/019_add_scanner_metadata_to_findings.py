"""Add scanner metadata columns to findings table.

Adds columns for external scanner integration: scanner_name, scanner_rule_id,
package, installed_version, fixed_version, cve, cwe, references, evidence.

Revision ID: 019
Revises: 018
Create Date: 2026-07-02 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision = "019"
down_revision = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("scanner_name", sa.String(100), nullable=True, index=True))
    op.add_column("findings", sa.Column("scanner_rule_id", sa.String(200), nullable=True))
    op.add_column("findings", sa.Column("package", sa.String(255), nullable=True, index=True))
    op.add_column("findings", sa.Column("installed_version", sa.String(100), nullable=True))
    op.add_column("findings", sa.Column("fixed_version", sa.String(100), nullable=True))
    op.add_column("findings", sa.Column("cve", sa.String(50), nullable=True, index=True))
    op.add_column("findings", sa.Column("cwe", sa.String(50), nullable=True))
    op.add_column("findings", sa.Column("references", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("evidence", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("findings", "evidence")
    op.drop_column("findings", "references")
    op.drop_column("findings", "cwe")
    op.drop_column("findings", "cve")
    op.drop_column("findings", "fixed_version")
    op.drop_column("findings", "installed_version")
    op.drop_column("findings", "package")
    op.drop_column("findings", "scanner_rule_id")
    op.drop_column("findings", "scanner_name")
