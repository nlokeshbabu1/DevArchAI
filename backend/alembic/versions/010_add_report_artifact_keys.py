"""add per-format report artifact keys

Revision ID: 010_add_report_artifact_keys
Revises: 009_add_github_login_to_users
Create Date: 2026-04-30 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "010_add_report_artifact_keys"
down_revision: Union[str, None] = "009_add_github_login_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add S3 keys for PDF and Excel report artifacts."""
    op.add_column("reports", sa.Column("pdf_s3_key", sa.String(length=500), nullable=True))
    op.add_column("reports", sa.Column("excel_s3_key", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Remove S3 keys for PDF and Excel report artifacts."""
    op.drop_column("reports", "excel_s3_key")
    op.drop_column("reports", "pdf_s3_key")
