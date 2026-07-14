"""Create missing base tables for models that predate Alembic.

These tables were originally created by create_all() and never received
a migration.  Every table is created with an idempotent guard so the
migration is safe to re-run.

Revision ID: 022
Revises: 021
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "022"
down_revision: str | None = "021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(conn, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def _has_column(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    try:
        cols = {c["name"] for c in insp.get_columns(table)}
        return column in cols
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()

    # ── Enum types used by multiple tables ──────────────────────────────
    plan_type_enum = sa.Enum("free", "pro", "enterprise", name="plantype")
    plan_type_enum.create(conn, checkfirst=True)

    membership_role_enum = sa.Enum("owner", "admin", "member", "viewer", name="membershiprole")
    membership_role_enum.create(conn, checkfirst=True)

    plan_interval_enum = sa.Enum("monthly", "yearly", name="plan_interval")
    plan_interval_enum.create(conn, checkfirst=True)

    subscription_status_enum = sa.Enum(
        "TRIAL", "ACTIVE", "PAST_DUE", "CANCELED", "EXPIRED",
        name="subscriptionstatus",
    )
    subscription_status_enum.create(conn, checkfirst=True)

    payment_type_enum = sa.Enum(
        "initial", "renewal", "upgrade", "downgrade", "refund", "one_time",
        name="payment_type",
    )
    payment_type_enum.create(conn, checkfirst=True)

    payment_status_enum = sa.Enum(
        "pending", "processing", "completed", "failed",
        "refunded", "partially_refunded", "disputed",
        name="payment_status",
    )
    payment_status_enum.create(conn, checkfirst=True)

    payment_provider_enum = sa.Enum("stripe", "razorpay", "paypal", name="payment_provider")
    payment_provider_enum.create(conn, checkfirst=True)

    invoice_status_enum = sa.Enum(
        "draft", "open", "paid", "uncollectible", "void", "pending",
        name="invoice_status",
    )
    invoice_status_enum.create(conn, checkfirst=True)

    coupon_type_enum = sa.Enum("percent", "fixed", "trial", name="coupon_type")
    coupon_type_enum.create(conn, checkfirst=True)

    fix_type_enum = sa.Enum(
        "terraform", "dockerfile", "kubernetes", "ci_cd", "general",
        name="fixtype",
    )
    fix_type_enum.create(conn, checkfirst=True)

    suggestion_status_enum = sa.Enum(
        "open", "in_progress", "fixed", "ignored",
        name="suggestionstatus",
    )
    suggestion_status_enum.create(conn, checkfirst=True)

    # ── 1. organizations ────────────────────────────────────────────────
    if not _has_table(conn, "organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False, index=True),
            sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("plan", plan_type_enum, nullable=False, server_default="free"),
            sa.Column("stripe_customer_id", sa.String(255), unique=True, nullable=True, index=True),
            sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
            sa.Column("scans_this_month", sa.Integer, nullable=False, server_default="0"),
            sa.Column("last_reset_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("settings", sa.Text, nullable=True),
            sa.Column("features", sa.Text, nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── 2. plans ────────────────────────────────────────────────────────
    if not _has_table(conn, "plans"):
        op.create_table(
            "plans",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("display_name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("interval", plan_interval_enum, nullable=False, server_default="monthly"),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("price_usd", sa.Integer, nullable=False, server_default="0"),
            sa.Column("price_inr", sa.Integer, nullable=False, server_default="0"),
            sa.Column("price_eur", sa.Integer, nullable=False, server_default="0"),
            sa.Column("price_gbp", sa.Integer, nullable=False, server_default="0"),
            sa.Column("stripe_price_id_monthly", sa.String(255), nullable=True),
            sa.Column("stripe_price_id_yearly", sa.String(255), nullable=True),
            sa.Column("razorpay_plan_id_monthly", sa.String(255), nullable=True),
            sa.Column("razorpay_plan_id_yearly", sa.String(255), nullable=True),
            sa.Column("features", postgresql.JSONB, nullable=False, server_default="{}"),
            sa.Column("trial_days", sa.Integer, nullable=False, server_default="0"),
            sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "price_usd >= 0 AND price_inr >= 0 AND price_eur >= 0 AND price_gbp >= 0",
                name="plans_price_non_negative",
            ),
        )

    # ── 3. organization_members ─────────────────────────────────────────
    if not _has_table(conn, "organization_members"):
        op.create_table(
            "organization_members",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "organization_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False, index=True,
            ),
            sa.Column(
                "user_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False, index=True,
            ),
            sa.Column("role", membership_role_enum, nullable=False, server_default="member"),
            sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
        )

    # ── 4. repositories ─────────────────────────────────────────────────
    if not _has_table(conn, "repositories"):
        op.create_table(
            "repositories",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=True, index=True,
            ),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("full_name", sa.String(500), nullable=True),
            sa.Column("url", sa.String(500), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("default_branch", sa.String(100), nullable=False, server_default="main"),
            sa.Column("is_private", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("github_id", sa.String(100), unique=True, nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── 5. anonymous_scans ──────────────────────────────────────────────
    if not _has_table(conn, "anonymous_scans"):
        op.create_table(
            "anonymous_scans",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("session_token", sa.String(255), unique=True, nullable=False, index=True),
            sa.Column("repository_url", sa.String(500), nullable=False),
            sa.Column("repository_name", sa.String(255), nullable=True),
            sa.Column("branch", sa.String(100), nullable=False, server_default="main"),
            sa.Column("linked_scan_id", sa.String(255), nullable=True),
            sa.Column("security_score", sa.String(10), nullable=True),
            sa.Column("critical_count", sa.String(10), nullable=True),
            sa.Column("high_count", sa.String(10), nullable=True),
            sa.Column("medium_count", sa.String(10), nullable=True),
            sa.Column("low_count", sa.String(10), nullable=True),
            sa.Column("findings_summary", sa.Text, nullable=True),
            sa.Column("ai_suggestions", sa.Text, nullable=True),
            sa.Column("status", sa.String(50), nullable=True, server_default="pending"),
            sa.Column("error_message", sa.Text, nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── 6. subscriptions ────────────────────────────────────────────────
    if not _has_table(conn, "subscriptions"):
        op.create_table(
            "subscriptions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "organization_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False, index=True,
            ),
            sa.Column("plan", postgresql.ENUM("FREE", "PRO", "ENTERPRISE", name="plantype", create_type=False),
                       nullable=False, server_default="FREE"),
            sa.Column("status", postgresql.ENUM("TRIAL", "ACTIVE", "PAST_DUE", "CANCELED", "EXPIRED",
                                                name="subscriptionstatus", create_type=False),
                       nullable=False, server_default="ACTIVE"),
            sa.Column("stripe_customer_id", sa.String(255), unique=True, nullable=True, index=True),
            sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
            sa.Column("stripe_price_id", sa.String(255), nullable=True),
            sa.Column("razorpay_customer_id", sa.String(255), nullable=True),
            sa.Column("razorpay_subscription_id", sa.String(255), nullable=True),
            sa.Column("provider", sa.String(50), nullable=True),
            sa.Column("billing_interval", sa.String(20), nullable=True),
            sa.Column(
                "plan_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("plans.id"), nullable=True,
            ),
            sa.Column("trial_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancel_at_period_end", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("scans_this_period", sa.Integer, nullable=False, server_default="0"),
            sa.Column("repositories_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("team_members_count", sa.Integer, nullable=False, server_default="1"),
            sa.Column("subscription_metadata", sa.Text, nullable=True),
            sa.Column("dunning_attempts", sa.Integer, nullable=False, server_default="0"),
            sa.Column("last_payment_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("grace_period_ends", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── 7. payments ─────────────────────────────────────────────────────
    if not _has_table(conn, "payments"):
        op.create_table(
            "payments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False, index=True,
            ),
            sa.Column(
                "subscription_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
                nullable=True, index=True,
            ),
            sa.Column("type", postgresql.ENUM("initial", "renewal", "upgrade", "downgrade", "refund", "one_time",
                                               name="payment_type", create_type=False),
                       nullable=False, server_default="initial"),
            sa.Column("status", postgresql.ENUM("pending", "processing", "completed", "failed",
                                                 "refunded", "partially_refunded", "disputed",
                                                 name="payment_status", create_type=False),
                       nullable=False, server_default="pending", index=True),
            sa.Column("provider", postgresql.ENUM("stripe", "razorpay", "paypal",
                                                   name="payment_provider", create_type=False),
                       nullable=False),
            sa.Column("amount", sa.Integer, nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("amount_refunded", sa.Integer, nullable=False, server_default="0"),
            sa.Column("provider_payment_id", sa.String(255), nullable=False),
            sa.Column("provider_order_id", sa.String(255), nullable=True),
            sa.Column("provider_invoice_id", sa.String(255), nullable=True),
            sa.Column("provider_response", postgresql.JSONB, nullable=True),
            sa.Column("failure_code", sa.String(100), nullable=True),
            sa.Column("failure_message", sa.Text, nullable=True),
            sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("extra_data", postgresql.JSONB, nullable=True, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "amount >= 0 AND amount_refunded >= 0",
                name="payments_amounts_non_negative",
            ),
        )

    # ── 8. invoices ─────────────────────────────────────────────────────
    if not _has_table(conn, "invoices"):
        op.create_table(
            "invoices",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False, index=True,
            ),
            sa.Column(
                "subscription_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
                nullable=True, index=True,
            ),
            sa.Column(
                "payment_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("payments.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("invoice_number", sa.String(50), unique=True, nullable=False, index=True),
            sa.Column("status", postgresql.ENUM("draft", "open", "paid", "uncollectible", "void", "pending",
                                                 name="invoice_status", create_type=False),
                       nullable=False, server_default="draft", index=True),
            sa.Column("subtotal", sa.Integer, nullable=False),
            sa.Column("tax_amount", sa.Integer, nullable=False, server_default="0"),
            sa.Column("discount_amount", sa.Integer, nullable=False, server_default="0"),
            sa.Column("total_amount", sa.Integer, nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("provider_invoice_id", sa.String(255), nullable=True),
            sa.Column("provider_hosted_url", sa.Text, nullable=True),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("pdf_url", sa.Text, nullable=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("extra_data", postgresql.JSONB, nullable=True, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("period_end >= period_start", name="invoices_period_check"),
            sa.CheckConstraint(
                "subtotal >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND total_amount >= 0",
                name="invoices_amounts_non_negative",
            ),
        )

    # ── 9. coupons ──────────────────────────────────────────────────────
    if not _has_table(conn, "coupons"):
        op.create_table(
            "coupons",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(50), unique=True, nullable=False, index=True),
            sa.Column("type", coupon_type_enum, nullable=False),
            sa.Column("value", sa.Integer, nullable=False),
            sa.Column("applicable_plans", postgresql.JSONB, nullable=True),
            sa.Column("max_redemptions", sa.Integer, nullable=True),
            sa.Column("redemption_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("max_redemptions_per_user", sa.Integer, nullable=False, server_default="1"),
            sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_months", sa.Integer, nullable=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── 10. webhook_events ──────────────────────────────────────────────
    if not _has_table(conn, "webhook_events"):
        op.create_table(
            "webhook_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("event_id", sa.String(255), nullable=False),
            sa.Column("event_type", sa.String(100), nullable=False),
            sa.Column("payload", postgresql.JSONB, nullable=False),
            sa.Column("processed", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("provider", "event_id", name="uq_webhook_events_provider_event"),
        )

    # ── 11. ai_suggestions ──────────────────────────────────────────────
    if not _has_table(conn, "ai_suggestions"):
        op.create_table(
            "ai_suggestions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "finding_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("findings.id", ondelete="CASCADE"),
                nullable=False, index=True,
            ),
            sa.Column(
                "scan_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("scans.id", ondelete="CASCADE"),
                nullable=False, index=True,
            ),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text, nullable=False),
            sa.Column("severity", sa.String(50), nullable=False, index=True),
            sa.Column("confidence", sa.Float, nullable=False, server_default="0.9"),
            sa.Column("category", sa.String(50), nullable=False, index=True),
            sa.Column("fix_type", fix_type_enum, nullable=False, server_default="general"),
            sa.Column("file_path", sa.String(500), nullable=False),
            sa.Column("line_number", sa.Integer, nullable=True),
            sa.Column("fix_code", sa.Text, nullable=True),
            sa.Column("auto_fix_available", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("status", suggestion_status_enum, nullable=False, server_default="open", index=True),
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("pr_url", sa.String(500), nullable=True),
            sa.Column("pr_number", sa.Integer, nullable=True),
            sa.Column("additional_data", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    conn = op.get_bind()

    tables_in_drop_order = [
        "ai_suggestions",
        "webhook_events",
        "coupons",
        "invoices",
        "payments",
        "subscriptions",
        "organization_members",
        "repositories",
        "anonymous_scans",
        "plans",
        "organizations",
    ]
    for table in tables_in_drop_order:
        if _has_table(conn, table):
            op.drop_table(table)

    enum_names = [
        "suggestionstatus", "fixtype", "coupon_type",
        "invoice_status", "payment_provider", "payment_status", "payment_type",
        "plan_interval", "subscriptionstatus", "membershiprole", "plantype",
    ]
    for name in enum_names:
        sa.Enum(name=name).drop(conn, checkfirst=True)
