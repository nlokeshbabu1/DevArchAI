"""enterprise auth phase 2: account lockout, os tracking, sso-ready fields

Revision ID: 017_enterprise_auth_phase2
Revises: 016_enterprise_auth
Create Date: 2026-05-31 01:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "017_enterprise_auth_phase2"
down_revision: Union[str, None] = "016_enterprise_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users: account lockout
    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    # Users: SSO-ready fields
    op.add_column("users", sa.Column("sso_provider", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("sso_id", sa.String(length=255), nullable=True))

    # UserSessions: OS field
    op.add_column("user_sessions", sa.Column("os", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("user_sessions", "os")
    op.drop_column("users", "sso_id")
    op.drop_column("users", "sso_provider")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
