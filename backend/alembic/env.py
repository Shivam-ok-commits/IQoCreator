"""Alembic environment configuration.

Supports both online mode (against a live database) and offline mode
(generating SQL scripts). The database URL is resolved in this order:

1. Command-line argument: ``alembic -x db_url=...``
2. Environment variable ``DATABASE_URL``
3. Application settings (from .env file)
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402

# Alembic Config object
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic autogenerate can detect them
from app.models import (  # noqa: F401
    User,
    ConnectedAccount,
    CreatorProfile,
    ChannelMetrics,
    Video,
    VideoMetrics,
    FeatureVector,
    ImportRun,
    AnalysisRun,
    RuleExecution,
    Evidence,
    ClaimEvidence,
    Claim,
    Recommendation,
    RecommendationFeedback,
    Experiment,
    ExperimentResult,
    MetricSnapshot,
    MetricFeatureVector,
    Finding,
    PipelineEvidence,
    PipelineClaim,
    PipelineRecommendation,
    PipelineExperiment,
)

# Target metadata for autogenerate
target_metadata = Base.metadata


def resolve_database_url() -> str:
    """Resolve the database URL from multiple sources.

    Priority:
    1. -x db_url=... CLI argument
    2. DATABASE_URL environment variable
    3. Application settings (from .env)
    """
    # Check for CLI argument
    x_args = context.get_x_argument(as_dictionary=True)
    if "db_url" in x_args:
        return x_args["db_url"]

    # Check environment variable
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # Fall back to settings
    return settings.sync_database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine,
    generating SQL scripts as strings that can be run directly.
    """
    url = resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine from the database URL and associates a
    connection with the context to run migrations against a live
    database.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = resolve_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
