"""add pdf_s3_key and excel_s3_key columns to reports

Revision ID: 013_add_report_storage_columns
Revises: 012_add_ai_status_to_scans
Create Date: 2026-05-07 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013_add_report_storage_columns"
down_revision: Union[str, None] = "012_add_ai_status_to_scans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("reports", "pdf_s3_key"):
        op.add_column(
            "reports",
            sa.Column("pdf_s3_key", sa.String(length=500), nullable=True),
        )

    if not _has_column("reports", "excel_s3_key"):
        op.add_column(
            "reports",
            sa.Column("excel_s3_key", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    if _has_column("reports", "excel_s3_key"):
        op.drop_column("reports", "excel_s3_key")

    if _has_column("reports", "pdf_s3_key"):
        op.drop_column("reports", "pdf_s3_key")
