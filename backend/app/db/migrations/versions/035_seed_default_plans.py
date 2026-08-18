"""Seed default subscription plans into the plans table.

Plans are inserted with ON CONFLICT DO NOTHING so this migration is
safe to re-run.  Stripe/Razorpay price IDs are left as NULL and must
be populated separately before payments will work end-to-end.

Revision ID: 035
Revises: 034
Create Date: 2026-08-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "035"
down_revision: str | None = "034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    plans = [
        (
            "free", "Free", "Perfect for getting started", "monthly",
            0, 0, 0, 0,
            '{"scans_per_month":3,"repositories":1,"ai_suggestions":false,"copy_fix":false,"report_exports":false,"github_automation":false,"team_features":false}',
            0, 1,
        ),
        (
            "plus", "Plus", "For individual developers", "monthly",
            1200, 99900, 1100, 1000,
            '{"scans_per_month":50,"repositories":5,"ai_suggestions":true,"copy_fix":true,"report_exports":true,"github_automation":false,"team_features":false}',
            14, 2,
        ),
        (
            "plus", "Plus", "For individual developers", "yearly",
            11520, 959040, 10560, 9600,
            '{"scans_per_month":50,"repositories":5,"ai_suggestions":true,"copy_fix":true,"report_exports":true,"github_automation":false,"team_features":false}',
            14, 2,
        ),
        (
            "pro", "Pro", "For professional DevOps engineers", "monthly",
            2900, 249900, 2600, 2400,
            '{"scans_per_month":-1,"repositories":-1,"ai_suggestions":true,"copy_fix":true,"report_exports":true,"github_automation":true,"team_features":true}',
            14, 3,
        ),
        (
            "pro", "Pro", "For professional DevOps engineers", "yearly",
            27840, 2399040, 24960, 23040,
            '{"scans_per_month":-1,"repositories":-1,"ai_suggestions":true,"copy_fix":true,"report_exports":true,"github_automation":true,"team_features":true}',
            14, 3,
        ),
        (
            "enterprise", "Enterprise", "For companies and teams", "monthly",
            9900, 799900, 8900, 7900,
            '{"scans_per_month":-1,"repositories":-1,"ai_suggestions":true,"copy_fix":true,"report_exports":true,"github_automation":true,"team_features":true,"compliance_reporting":true,"custom_security_rules":true,"dedicated_support":true}',
            0, 4,
        ),
        (
            "enterprise", "Enterprise", "For companies and teams", "yearly",
            95040, 7679040, 85440, 75840,
            '{"scans_per_month":-1,"repositories":-1,"ai_suggestions":true,"copy_fix":true,"report_exports":true,"github_automation":true,"team_features":true,"compliance_reporting":true,"custom_security_rules":true,"dedicated_support":true}',
            0, 4,
        ),
    ]

    conn = op.get_bind()
    raw_conn = conn.connection.connection

    for name, display, desc, interval, p_usd, p_inr, p_eur, p_gbp, features, trial, sort in plans:
        raw_conn.cursor().execute(
            """
            INSERT INTO plans
                (id, name, display_name, description, interval, is_active,
                 price_usd, price_inr, price_eur, price_gbp,
                 features, trial_days, sort_order, created_at, updated_at)
            VALUES
                (gen_random_uuid(), %s, %s, %s,
                 %s::plan_interval, true,
                 %s, %s, %s, %s,
                 %s::jsonb,
                 %s, %s, now(), now())
            ON CONFLICT DO NOTHING
            """,
            (name, display, desc, interval, p_usd, p_inr, p_eur, p_gbp, features, trial, sort),
        )
    raw_conn.commit()


def downgrade() -> None:
    op.execute("DELETE FROM plans WHERE name IN ('free', 'plus', 'pro', 'enterprise')")
