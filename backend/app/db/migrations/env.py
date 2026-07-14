"""Alembic configuration for database migrations."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401
import app.models.ai_suggestion  # noqa: F401
import app.models.audit_log  # noqa: F401
import app.models.aws  # noqa: F401
import app.models.finding  # noqa: F401
import app.models.github_installation  # noqa: F401
import app.models.organization  # noqa: F401
import app.models.payment  # noqa: F401
import app.models.pull_request  # noqa: F401
import app.models.repo_analysis  # noqa: F401
import app.models.report  # noqa: F401
import app.models.repository  # noqa: F401
import app.models.scan  # noqa: F401
import app.models.settings  # noqa: F401
import app.models.subscription  # noqa: F401
import app.models.user  # noqa: F401
from alembic import context
from app.config import settings

# Import all models so Alembic autogenerate detects schema changes
from app.db.base import Base

# this is the Alembic Config object
alembic_config = context.config

# Set the database URL from settings
# Convert asyncpg URL to psycopg2 for Alembic CLI
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
elif db_url.startswith("postgresql://"):
    pass  # Already sync driver
alembic_config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = alembic_config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
