-- Migration: Add production-grade payment and billing system
-- Date: 2025-04-09
-- Description: Adds plans, payments, invoices, coupons, and webhook_events tables.
--              Extends users and subscriptions tables with billing fields.

-- ─── New Enums ─────────────────────────────────────────────────────────

CREATE TYPE plan_interval AS ENUM ('monthly', 'yearly');

CREATE TYPE payment_status AS ENUM (
    'pending', 'processing', 'completed', 'failed', 'refunded', 'partially_refunded', 'disputed'
);

CREATE TYPE payment_type AS ENUM (
    'initial', 'renewal', 'upgrade', 'downgrade', 'refund', 'one_time'
);

CREATE TYPE payment_provider AS ENUM ('stripe', 'razorpay', 'paypal');

CREATE TYPE invoice_status AS ENUM (
    'draft', 'open', 'paid', 'uncollectible', 'void', 'pending'
);

CREATE TYPE coupon_type AS ENUM ('percent', 'fixed', 'trial');

-- ─── Plans Table ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(50) NOT NULL,
    display_name    VARCHAR(100) NOT NULL,
    description     TEXT,
    interval        plan_interval NOT NULL DEFAULT 'monthly',
    is_active       BOOLEAN NOT NULL DEFAULT true,

    -- Pricing in smallest currency unit (cents/paise)
    price_usd       INTEGER NOT NULL DEFAULT 0,
    price_inr       INTEGER NOT NULL DEFAULT 0,
    price_eur       INTEGER NOT NULL DEFAULT 0,
    price_gbp       INTEGER NOT NULL DEFAULT 0,

    -- Provider plan IDs
    stripe_price_id_monthly   VARCHAR(255),
    stripe_price_id_yearly    VARCHAR(255),
    razorpay_plan_id_monthly  VARCHAR(255),
    razorpay_plan_id_yearly   VARCHAR(255),

    -- Features as JSON
    features        JSONB NOT NULL DEFAULT '{}',

    -- Trial
    trial_days      INTEGER NOT NULL DEFAULT 0,

    -- Metadata
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT plans_name_interval_unique UNIQUE (name, interval),
    CONSTRAINT plans_price_non_negative CHECK (
        price_usd >= 0 AND price_inr >= 0 AND price_eur >= 0 AND price_gbp >= 0
    )
);

CREATE INDEX idx_plans_active ON plans (is_active) WHERE is_active = true;
CREATE INDEX idx_plans_interval ON plans (interval);

-- ─── Payments Table ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS payments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id     UUID REFERENCES subscriptions(id) ON DELETE SET NULL,

    -- Payment details
    type                payment_type NOT NULL DEFAULT 'initial',
    status              payment_status NOT NULL DEFAULT 'pending',
    provider            payment_provider NOT NULL,

    -- Amount in smallest currency unit
    amount              INTEGER NOT NULL,
    currency            VARCHAR(3) NOT NULL,
    amount_refunded     INTEGER NOT NULL DEFAULT 0,

    -- Provider references
    provider_payment_id VARCHAR(255) NOT NULL,
    provider_order_id   VARCHAR(255),
    provider_invoice_id VARCHAR(255),

    -- Raw provider response
    provider_response   JSONB,

    -- Failure tracking
    failure_code        VARCHAR(100),
    failure_message     TEXT,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    next_retry_at       TIMESTAMPTZ,

    -- Metadata
    description         TEXT,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- CRITICAL: Prevent duplicate payments from webhook replay
    CONSTRAINT payments_provider_unique UNIQUE (provider, provider_payment_id),
    CONSTRAINT payments_amounts_non_negative CHECK (amount >= 0 AND amount_refunded >= 0)
);

CREATE INDEX idx_payments_user_id ON payments (user_id);
CREATE INDEX idx_payments_subscription_id ON payments (subscription_id);
CREATE INDEX idx_payments_status ON payments (status);
CREATE INDEX idx_payments_provider_payment ON payments (provider, provider_payment_id);
CREATE INDEX idx_payments_created ON payments (created_at DESC);

-- ─── Invoices Table ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS invoices (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id     UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    payment_id          UUID REFERENCES payments(id) ON DELETE SET NULL,

    invoice_number      VARCHAR(50) NOT NULL UNIQUE,
    status              invoice_status NOT NULL DEFAULT 'draft',

    -- Amounts in smallest currency unit
    subtotal            INTEGER NOT NULL,
    tax_amount          INTEGER NOT NULL DEFAULT 0,
    discount_amount     INTEGER NOT NULL DEFAULT 0,
    total_amount        INTEGER NOT NULL,
    currency            VARCHAR(3) NOT NULL,

    -- Provider references
    provider_invoice_id VARCHAR(255),
    provider_hosted_url TEXT,

    -- Billing period
    period_start        TIMESTAMPTZ NOT NULL,
    period_end          TIMESTAMPTZ NOT NULL,
    due_date            TIMESTAMPTZ,

    -- PDF
    pdf_url             TEXT,

    -- Metadata
    description         TEXT,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT invoices_period_check CHECK (period_end >= period_start),
    CONSTRAINT invoices_amounts_non_negative CHECK (
        subtotal >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND total_amount >= 0
    )
);

CREATE INDEX idx_invoices_user_id ON invoices (user_id);
CREATE INDEX idx_invoices_subscription_id ON invoices (subscription_id);
CREATE INDEX idx_invoices_status ON invoices (status);
CREATE INDEX idx_invoices_period ON invoices (period_start, period_end);

-- ─── Coupons Table ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS coupons (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code                VARCHAR(50) NOT NULL UNIQUE,
    type                coupon_type NOT NULL,
    value               INTEGER NOT NULL,

    -- Applicability
    applicable_plans    JSONB DEFAULT NULL,
    max_redemptions     INTEGER DEFAULT NULL,
    redemption_count    INTEGER NOT NULL DEFAULT 0,
    max_redemptions_per_user INTEGER NOT NULL DEFAULT 1,

    -- Validity
    valid_from          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until         TIMESTAMPTZ,
    duration_months     INTEGER DEFAULT NULL,

    -- Metadata
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT coupons_value_check CHECK (
        (type = 'percent' AND value BETWEEN 1 AND 100) OR
        (type = 'fixed' AND value > 0) OR
        (type = 'trial' AND value > 0)
    )
);

CREATE INDEX idx_coupons_active ON coupons (valid_from, valid_until)
    WHERE valid_until IS NULL OR valid_until > NOW();

-- ─── Webhook Events Table ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS webhook_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider            VARCHAR(50) NOT NULL,
    event_id            VARCHAR(255) NOT NULL,
    event_type          VARCHAR(100) NOT NULL,
    payload             JSONB NOT NULL,
    processed           BOOLEAN NOT NULL DEFAULT false,
    processed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT webhook_events_provider_event_unique UNIQUE (provider, event_id)
);

CREATE INDEX idx_webhook_events_processed ON webhook_events (processed) WHERE processed = false;

-- ─── Extend Users Table ────────────────────────────────────────────────

ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(2) DEFAULT 'US';
ALTER TABLE users ADD COLUMN IF NOT EXISTS billing_email VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS tax_id VARCHAR(100);

-- ─── Extend Subscriptions Table ────────────────────────────────────────

ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS provider VARCHAR(50);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS billing_interval VARCHAR(20);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS plan_id UUID REFERENCES plans(id);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS razorpay_customer_id VARCHAR(255);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS razorpay_subscription_id VARCHAR(255);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS dunning_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS last_payment_at TIMESTAMPTZ;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS last_payment_id UUID;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS grace_period_ends TIMESTAMPTZ;

-- ─── Seed Default Plans ────────────────────────────────────────────────

INSERT INTO plans (name, display_name, description, interval, price_usd, price_inr, price_eur, price_gbp,
                   features, trial_days, sort_order)
VALUES
('free', 'Free', 'Get started with basic security scanning', 'monthly', 0, 0, 0, 0,
 '{"max_repositories": 5, "max_scans_per_month": 10, "ai_suggestions": false, "api_access": false, "priority_support": false}',
 0, 0)
ON CONFLICT (name, interval) DO NOTHING;

INSERT INTO plans (name, display_name, description, interval, price_usd, price_inr, price_eur, price_gbp,
                   features, trial_days, sort_order)
VALUES
('plus', 'Plus', 'Advanced scanning with AI suggestions', 'monthly', 999, 49900, 999, 799,
 '{"max_repositories": 50, "max_scans_per_month": 100, "ai_suggestions": true, "api_access": false, "priority_support": false}',
 14, 1)
ON CONFLICT (name, interval) DO NOTHING;

INSERT INTO plans (name, display_name, description, interval, price_usd, price_inr, price_eur, price_gbp,
                   features, trial_days, sort_order)
VALUES
('plus', 'Plus', 'Advanced scanning with AI suggestions (annual)', 'yearly', 9990, 499900, 9990, 7990,
 '{"max_repositories": 50, "max_scans_per_month": 100, "ai_suggestions": true, "api_access": false, "priority_support": false}',
 14, 1)
ON CONFLICT (name, interval) DO NOTHING;

INSERT INTO plans (name, display_name, description, interval, price_usd, price_inr, price_eur, price_gbp,
                   features, trial_days, sort_order)
VALUES
('pro', 'Pro', 'Team features with unlimited scanning', 'monthly', 2999, 149900, 2999, 2399,
 '{"max_repositories": -1, "max_scans_per_month": -1, "ai_suggestions": true, "api_access": true, "priority_support": true, "team_members": 10}',
 14, 2)
ON CONFLICT (name, interval) DO NOTHING;

INSERT INTO plans (name, display_name, description, interval, price_usd, price_inr, price_eur, price_gbp,
                   features, trial_days, sort_order)
VALUES
('pro', 'Pro', 'Team features with unlimited scanning (annual)', 'yearly', 29990, 1499900, 29990, 23990,
 '{"max_repositories": -1, "max_scans_per_month": -1, "ai_suggestions": true, "api_access": true, "priority_support": true, "team_members": 10}',
 14, 2)
ON CONFLICT (name, interval) DO NOTHING;

INSERT INTO plans (name, display_name, description, interval, price_usd, price_inr, price_eur, price_gbp,
                   features, trial_days, sort_order)
VALUES
('enterprise', 'Enterprise', 'Custom deployment with dedicated support', 'monthly', 9999, 499900, 9999, 7999,
 '{"max_repositories": -1, "max_scans_per_month": -1, "ai_suggestions": true, "api_access": true, "priority_support": true, "team_members": -1, "sso": true, "audit_logs": true}',
 30, 3)
ON CONFLICT (name, interval) DO NOTHING;
