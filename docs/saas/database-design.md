# DevArchAI - Database Design Document

> **Version:** 1.0.0  
> **Status:** Production-Ready  
> **Last Updated:** April 14, 2026

---

## 1. Overview

This document defines the complete database schema for DevArchAI, including entity relationships, indexes, constraints, and migration strategy.

**Database:** PostgreSQL 15  
**ORM:** SQLAlchemy 2.0 (Async)  
**Migration Tool:** Alembic

---

## 2. Entity Relationship Diagram

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   users         │       │  organizations   │       │  repositories   │
├─────────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)          │    ┌──│ id (PK)         │
│ email_encrypted │  │    │ name             │    │  │ user_id (FK)    │
│ email_hash      │  │    │ slug             │    │  │ name            │
│ username        │  │    │ plan             │    │  │ url             │
│ hashed_password │  └───<│ created_at       │    │  │ default_branch  │
│ github_id       │       └──────────────────┘    └──│ is_private      │
│ role            │                                 │ last_scanned_at │
│ subscription_plan│                                └────────┬────────┘
│ created_at      │                                          │
└────────┬────────┘                                          │
         │                                                   │
         │                                                   │
         ▼                                                   ▼
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│ subscriptions   │       │     scans        │       │   findings      │
├─────────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)          │       │ id (PK)         │
│ user_id (FK)    │       │ repository_id(FK)│       │ scan_id (FK)    │
│ provider        │       │ user_id (FK)     │       │ rule_id         │
│ provider_sub_id │       │ status           │       │ severity        │
│ plan            │       │ progress         │       │ category        │
│ status          │       │ overall_score    │       │ description     │
│ period_start    │       │ security_score   │       │ recommendation  │
│ period_end      │       │ detected_stack   │       │ file_path       │
│ created_at      │       │ celery_task_id   │       │ ai_explanation  │
└─────────────────┘       │ started_at       │       │ fix_code        │
                          │ completed_at     │       │ confidence_score│
                          └────────┬─────────┘       │ created_at      │
                                   │                 └────────┬────────┘
                                   │                          │
                                   ▼                          │
                          ┌──────────────────┐                │
                          │ pull_requests    │                │
                          ├──────────────────┤                │
                          │ id (PK)          │                │
                          │ scan_id (FK)     │────────────────┘
                          │ github_pr_number │
                          │ github_pr_url    │
                          │ branch_name      │
                          │ status           │
                          │ created_at       │
                          └──────────────────┘
```

---

## 3. Table Definitions

### 3.1 users

**Purpose:** Store user account information with encrypted PII

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_encrypted VARCHAR(255) NOT NULL,
    email_hash VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    hashed_password VARCHAR(255),
    github_id VARCHAR(100),
    github_access_token TEXT,
    role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('user', 'admin', 'owner')),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    subscription_plan VARCHAR(20) DEFAULT 'free' 
        CHECK (subscription_plan IN ('free', 'plus', 'pro', 'enterprise')),
    current_org_id UUID,
    api_key VARCHAR(255),
    api_key_prefix VARCHAR(8),
    country VARCHAR(2) DEFAULT 'US',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);

-- Indexes
CREATE UNIQUE INDEX idx_users_email_hash ON users(email_hash);
CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_github_id ON users(github_id);
CREATE INDEX idx_users_subscription_plan ON users(subscription_plan);
CREATE INDEX idx_users_current_org ON users(current_org_id);
```

**Security Notes:**
- `email_encrypted`: AES-256 encrypted email address
- `email_hash`: SHA-256 hash for fast lookups during login
- `github_access_token`: Encrypted at rest
- `api_key`: Hashed before storage, only prefix shown to user

---

### 3.2 organizations

**Purpose:** Multi-tenant organization management with team workspaces

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(20) DEFAULT 'free' 
        CHECK (plan IN ('free', 'plus', 'pro', 'enterprise')),
    github_org_id VARCHAR(100),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member' 
        CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- Indexes
CREATE UNIQUE INDEX idx_orgs_slug ON organizations(slug);
CREATE INDEX idx_orgs_github_id ON organizations(github_org_id);
CREATE INDEX idx_org_members_org ON organization_members(organization_id);
CREATE INDEX idx_org_members_user ON organization_members(user_id);
```

---

### 3.3 repositories

**Purpose:** Track scanned GitHub repositories and their metadata

```sql
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) UNIQUE NOT NULL,
    default_branch VARCHAR(100) DEFAULT 'main',
    is_private BOOLEAN DEFAULT false,
    github_repo_id VARCHAR(100),
    description TEXT,
    language VARCHAR(50),
    last_scanned_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX idx_repos_url ON repositories(url);
CREATE INDEX idx_repos_user ON repositories(user_id);
CREATE INDEX idx_repos_org ON repositories(organization_id);
CREATE INDEX idx_repos_github_id ON repositories(github_repo_id);
CREATE INDEX idx_repos_last_scanned ON repositories(last_scanned_at);
```

---

### 3.4 scans

**Purpose:** Track scan executions, progress, and results

```sql
CREATE TYPE scan_status AS ENUM ('pending', 'queued', 'processing', 'completed', 'failed', 'cancelled');

CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    repository_url VARCHAR(500) NOT NULL,
    branch VARCHAR(100) DEFAULT 'main',
    commit_hash VARCHAR(40),
    status scan_status DEFAULT 'pending',
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    status_message VARCHAR(500),
    error_message TEXT,
    
    -- Scores
    overall_score FLOAT CHECK (overall_score >= 0 AND overall_score <= 100),
    security_score FLOAT CHECK (security_score >= 0 AND security_score <= 100),
    scalability_score FLOAT CHECK (scalability_score >= 0 AND scalability_score <= 100),
    reliability_score FLOAT CHECK (reliability_score >= 0 AND reliability_score <= 100),
    cost_score FLOAT CHECK (cost_score >= 0 AND cost_score <= 100),
    observability_score FLOAT CHECK (observability_score >= 0 AND observability_score <= 100),
    
    -- Metadata
    detected_stack JSONB,
    files_analyzed INTEGER DEFAULT 0,
    celery_task_id VARCHAR(255),
    
    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    analysis_duration_seconds FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_scans_user ON scans(user_id);
CREATE INDEX idx_scans_repository ON scans(repository_id);
CREATE INDEX idx_scans_status ON scans(status);
CREATE INDEX idx_scans_created_at ON scans(created_at DESC);
CREATE INDEX idx_scans_celery_task ON scans(celery_task_id);
CREATE INDEX idx_scans_overall_score ON scans(overall_score);

-- Partial index for active scans
CREATE INDEX idx_scans_active ON scans(id) 
    WHERE status IN ('pending', 'queued', 'processing');
```

---

### 3.5 findings

**Purpose:** Store individual rule violations and AI-generated suggestions

```sql
CREATE TYPE finding_severity AS ENUM ('critical', 'high', 'medium', 'low', 'info');
CREATE TYPE finding_category AS ENUM ('security', 'scalability', 'reliability', 'cost', 'observability');

CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    rule_id VARCHAR(50) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    severity finding_severity NOT NULL,
    category finding_category NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    file_path VARCHAR(500),
    line_number INTEGER,
    resource_name VARCHAR(255),
    
    -- AI-generated fields
    ai_explanation TEXT,
    ai_generated BOOLEAN DEFAULT false,
    impact_analysis TEXT,
    fix_code TEXT,
    fix_example TEXT,
    full_example TEXT,
    best_practices JSONB,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    documentation_url VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_findings_scan ON findings(scan_id);
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_category ON findings(category);
CREATE INDEX idx_findings_rule_id ON findings(rule_id);
CREATE INDEX idx_findings_file_path ON findings(file_path);

-- Composite indexes for common queries
CREATE INDEX idx_findings_scan_severity ON findings(scan_id, severity);
CREATE INDEX idx_findings_scan_category ON findings(scan_id, category);
```

---

### 3.6 pull_requests

**Purpose:** Track automated GitHub PRs created with AI fixes

```sql
CREATE TYPE pr_status AS ENUM ('open', 'merged', 'closed', 'draft');

CREATE TABLE pull_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    github_pr_number INTEGER NOT NULL,
    github_pr_url VARCHAR(500) NOT NULL,
    branch_name VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status pr_status DEFAULT 'open',
    findings_fixed JSONB,
    score_before FLOAT,
    score_after FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    merged_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_prs_scan ON pull_requests(scan_id);
CREATE INDEX idx_prs_user ON pull_requests(user_id);
CREATE INDEX idx_prs_github_number ON pull_requests(github_pr_number);
CREATE INDEX idx_prs_status ON pull_requests(status);
CREATE INDEX idx_prs_created_at ON pull_requests(created_at DESC);
```

---

### 3.7 subscriptions

**Purpose:** Manage user subscriptions and billing information

```sql
CREATE TYPE subscription_provider AS ENUM ('stripe', 'razorpay', 'paypal');
CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'past_due', 'trialing', 'unpaid');

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider subscription_provider NOT NULL,
    provider_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    provider_customer_id VARCHAR(255),
    plan VARCHAR(20) NOT NULL 
        CHECK (plan IN ('plus', 'pro', 'enterprise')),
    status subscription_status DEFAULT 'active',
    quantity INTEGER DEFAULT 1,
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMP,
    trial_start TIMESTAMP,
    trial_end TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_subs_user ON subscriptions(user_id);
CREATE INDEX idx_subs_provider_id ON subscriptions(provider_subscription_id);
CREATE INDEX idx_subs_status ON subscriptions(status);
CREATE INDEX idx_subs_period_end ON subscriptions(current_period_end);
CREATE INDEX idx_subs_plan ON subscriptions(plan);
```

---

### 3.8 payments

**Purpose:** Track payment transactions and invoices

```sql
CREATE TYPE payment_status AS ENUM ('pending', 'succeeded', 'failed', 'refunded');

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    provider payment_provider NOT NULL,
    provider_payment_id VARCHAR(255) UNIQUE NOT NULL,
    provider_invoice_id VARCHAR(255),
    amount INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status payment_status DEFAULT 'pending',
    receipt_url VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    paid_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_subscription ON payments(subscription_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created_at ON payments(created_at DESC);
```

---

### 3.9 ai_suggestions

**Purpose:** Cache AI-generated suggestions to reduce API costs

```sql
CREATE TABLE ai_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID REFERENCES findings(id) ON DELETE CASCADE,
    prompt_hash VARCHAR(64) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    explanation TEXT,
    impact_analysis TEXT,
    fix_code TEXT,
    fix_example TEXT,
    best_practices JSONB,
    confidence_score FLOAT,
    tokens_used INTEGER,
    cost_usd FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(prompt_hash, provider, model)
);

-- Indexes
CREATE INDEX idx_ai_suggestions_finding ON ai_suggestions(finding_id);
CREATE UNIQUE INDEX idx_ai_suggestions_prompt_hash ON ai_suggestions(prompt_hash, provider, model);
CREATE INDEX idx_ai_suggestions_created_at ON ai_suggestions(created_at DESC);
```

---

### 3.10 audit_logs

**Purpose:** Immutable audit trail for compliance and debugging

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    status_code INTEGER,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Note: This table should be append-only with DELETE permissions restricted
```

---

## 4. Database Constraints & Rules

### Foreign Key Cascade Rules

| Parent Table | Child Table | On Delete | On Update |
|--------------|-------------|-----------|-----------|
| users | repositories | CASCADE | CASCADE |
| users | scans | SET NULL | CASCADE |
| users | subscriptions | CASCADE | CASCADE |
| repositories | scans | CASCADE | CASCADE |
| scans | findings | CASCADE | CASCADE |
| scans | pull_requests | CASCADE | CASCADE |

### Check Constraints

```sql
-- Score ranges
CHECK (score >= 0 AND score <= 100)

-- Progress percentage
CHECK (progress >= 0 AND progress <= 100)

-- Confidence score
CHECK (confidence_score >= 0 AND confidence_score <= 1)

-- Enum validations
CHECK (role IN ('user', 'admin', 'owner'))
CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled'))
```

---

## 5. Migration Strategy

### Alembic Configuration

```python
# alembic.ini
[alembic]
script_location = backend/app/db/migrations
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai

# Migration workflow
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### Migration Best Practices

1. **Never modify existing migrations** - Always create new migration
2. **Test migrations** - Run on staging before production
3. **Backward compatible** - Support old and new schema during transition
4. **Data migrations** - Separate from schema migrations
5. **Rollback plan** - Always test downgrade path

---

## 6. Performance Optimization

### Indexing Strategy

**High-Cardinality Indexes:**
- Primary keys (UUID)
- Unique constraints (email, username, URLs)
- Foreign keys (user_id, scan_id, repository_id)

**Low-Cardinality Indexes:**
- Status fields (scan_status, subscription_status)
- Enum fields (severity, category)
- Boolean flags (is_active, is_private)

**Composite Indexes:**
- `(scan_id, severity)` - Filter findings by scan and severity
- `(scan_id, category)` - Filter findings by scan and category
- `(user_id, created_at DESC)` - User's recent scans

### Query Optimization

```sql
-- Use EXPLAIN ANALYZE for slow queries
EXPLAIN ANALYZE 
SELECT * FROM findings 
WHERE scan_id = 'xxx' AND severity = 'critical';

-- Avoid SELECT * in production
SELECT id, rule_id, severity, description FROM findings WHERE scan_id = 'xxx';

-- Use LIMIT for pagination
SELECT * FROM scans WHERE user_id = 'xxx' ORDER BY created_at DESC LIMIT 20 OFFSET 0;
```

### Connection Pooling

```python
# SQLAlchemy async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    echo=False
)
```

---

## 7. Backup & Recovery

### Backup Strategy

```bash
# Daily automated backup
pg_dump -U postgres -d devarchai -F c -f /backups/devarchai_$(date +%Y%m%d).dump

# Weekly full backup with compression
pg_dump -U postgres -d devarchai -F c -Z 9 -f /backups/weekly_$(date +%Y%m%d).dump.gz

# Point-in-time recovery with WAL archiving
archive_mode = on
archive_command = 'cp %p /backups/wal/%f'
```

### Recovery Procedures

```bash
# Restore from backup
pg_restore -U postgres -d devarchai -c /backups/devarchai_20260414.dump

# Point-in-time recovery
recovery_target_time = '2026-04-14 10:30:00'
```

---

## 8. Data Retention Policy

| Data Type | Retention Period | Action |
|-----------|------------------|--------|
| Anonymous scans | 7 days | Auto-delete |
| User scans | Indefinite | User can delete |
| Findings | Tied to scan | Cascade delete |
| Audit logs | 1 year | Archive to S3 |
| AI suggestions | 30 days | Cache invalidation |
| Payment records | 7 years | Compliance requirement |
| Expired sessions | 24 hours | Auto-cleanup |

### Cleanup Jobs

```python
# Celery periodic task
@celery_app.task
def cleanup_expired_data():
    # Delete anonymous scans older than 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    db.execute(
        delete(Scan).where(
            Scan.user_id.is_(None),
            Scan.created_at < seven_days_ago
        )
    )
    
    # Delete expired sessions
    db.execute(delete(Session).where(Session.expires_at < datetime.utcnow()))
    
    db.commit()
```

---

*This document is maintained by the DevArchAI engineering team. Last reviewed: April 14, 2026.*
