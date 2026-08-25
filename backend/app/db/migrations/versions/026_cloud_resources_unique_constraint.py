"""Add account_id and unique constraint to cloud_resources.

Adds the account_id column (denormalized from cloud_connections) and a
unique index on (connection_id, provider, region, resource_id) to support
upsert operations in the repository layer.

Revision ID: 026
Revises: 025
Create Date: 2025-02-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "026"
down_revision = "025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add account_id column (denormalized from cloud_connections)
    op.add_column(
        "cloud_resources",
        sa.Column(
            "account_id",
            sa.String(128),
            nullable=False,
            server_default="",
        ),
    )

    # Backfill account_id from cloud_connections
    op.execute(
        """
        UPDATE cloud_resources cr
        SET account_id = cc.account_id
        FROM cloud_connections cc
        WHERE cr.connection_id = cc.id
        AND cr.account_id = ''
        """
    )

    # Create unique index for upsert: (connection_id, provider, region, resource_id)
    # This is the natural unique key for cloud resources.
    op.create_index(
        "uq_cloud_resources_conn_provider_region_resource",
        "cloud_resources",
        ["connection_id", "provider", "region", "resource_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_cloud_resources_conn_provider_region_resource",
        table_name="cloud_resources",
    )
    op.drop_column("cloud_resources", "account_id")
