"""Add finding processing_metadata JSON column."""

from alembic import op
import sqlalchemy as sa

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column("processing_metadata", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("findings", "processing_metadata")
