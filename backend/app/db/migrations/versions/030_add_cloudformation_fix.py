"""Add cloudformation_fix column to cloud_ai_recommendations.

Adds the cloudformation_fix Text column alongside the existing
terraform_fix and aws_cli_fix columns for structured remediation.

Revision ID: 030
Revises: 029
"""
import sqlalchemy as sa

from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cloud_ai_recommendations",
        sa.Column("cloudformation_fix", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cloud_ai_recommendations", "cloudformation_fix")
