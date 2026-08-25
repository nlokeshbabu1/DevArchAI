"""Bootstrap core legacy tables.

users/scans/findings/reports were historically created only by
Base.metadata.create_all() at application startup, so ``alembic upgrade
head`` crashed on any clean database (002 alters findings before anything
creates it).  This root migration creates them with IF NOT EXISTS guards,
excluding every column that a later migration adds itself and outbound
FKs whose target tables are created by later revisions.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "000"
down_revision = None
branch_labels = None
depends_on = None

_DDL = """
DO $$ BEGIN
    CREATE TYPE userrole AS ENUM ('USER', 'ADMIN', 'ENTERPRISE');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE scanstatus AS ENUM ('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE severity AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE category AS ENUM ('SECURITY', 'SCALABILITY', 'RELIABILITY', 'COST', 'OBSERVABILITY');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS users (
	id UUID NOT NULL, 
	username VARCHAR(100) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255), 
	avatar_url VARCHAR(500), 
	github_id VARCHAR(100), 
	github_access_token VARCHAR(500), 
	gitlab_id VARCHAR(100), 
	gitlab_username VARCHAR(100), 
	gitlab_access_token VARCHAR(500), 
	is_active BOOLEAN NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	role userrole NOT NULL, 
	subscription_plan VARCHAR(50) NOT NULL, 
	country VARCHAR(2), 
	billing_email VARCHAR(255), 
	tax_id VARCHAR(100), 
	current_org_id UUID, 
	api_key VARCHAR(255), 
	api_key_prefix VARCHAR(8), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (github_id), 
	UNIQUE (gitlab_id), 
	UNIQUE (api_key)
);

CREATE TABLE IF NOT EXISTS scans (
	id UUID NOT NULL, 
	user_id UUID, 
	repository_id UUID, 
	repository_url VARCHAR(500) NOT NULL, 
	branch VARCHAR(100) NOT NULL, 
	commit_hash VARCHAR(40), 
	status scanstatus NOT NULL, 
	progress INTEGER NOT NULL, 
	error_message TEXT, 
	celery_task_id VARCHAR(255), 
	overall_score FLOAT, 
	security_score FLOAT, 
	scalability_score FLOAT, 
	reliability_score FLOAT, 
	cost_score FLOAT, 
	observability_score FLOAT, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	analysis_duration_seconds FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_scans_user_id FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS findings (
	id UUID NOT NULL, 
	scan_id UUID NOT NULL, 
	rule_id VARCHAR(50) NOT NULL, 
	rule_name VARCHAR(255) NOT NULL, 
	severity severity NOT NULL, 
	category category NOT NULL, 
	description TEXT NOT NULL, 
	recommendation TEXT NOT NULL, 
	risk TEXT, 
	impact TEXT, 
	fix_example TEXT, 
	file_path VARCHAR(500), 
	line_number INTEGER, 
	resource_name VARCHAR(255), 
	ai_explanation TEXT, 
	impact_analysis TEXT, 
	confidence FLOAT, 
	confidence_score FLOAT NOT NULL, 
	is_resolved BOOLEAN NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_findings_scan_id FOREIGN KEY(scan_id) REFERENCES scans (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports (
	id UUID NOT NULL, 
	scan_id UUID NOT NULL, 
	repository_name VARCHAR(255) NOT NULL, 
	repository_url VARCHAR(500) NOT NULL, 
	commit_hash VARCHAR(40), 
	overall_score FLOAT NOT NULL, 
	category_scores JSON, 
	executive_summary TEXT, 
	risk_analysis TEXT, 
	prioritized_recommendations JSON, 
	total_findings INTEGER NOT NULL, 
	critical_count INTEGER NOT NULL, 
	high_count INTEGER NOT NULL, 
	medium_count INTEGER NOT NULL, 
	low_count INTEGER NOT NULL, 
	info_count INTEGER NOT NULL, 
	files_analyzed JSON, 
	s3_key VARCHAR(500), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (scan_id), 
	CONSTRAINT fk_reports_scan_id FOREIGN KEY(scan_id) REFERENCES scans (id) ON DELETE CASCADE
)"""

def upgrade() -> None:
    op.execute(_DDL)


def downgrade() -> None:
    # Core tables predate the migration chain and may hold live data; leaving
    # them in place on downgrade is intentional.
    pass
