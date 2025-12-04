import os
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from yourapp.models import Base  # replace with your SQLAlchemy Base

# Alembic Config object
config = context.config

# Logging setup
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# ---------------------------
# Hardcoded DB URL
# ---------------------------
DB_URL = "postgresql://damko:damko@bee_db:5432/lab2"
config.set_main_option("sqlalchemy.url", DB_URL)

# Set target metadata for autogenerate
target_metadata = Base.metadata  # replace Base with your declarative_base

# ---------------------------
# Offline migrations
# ---------------------------
def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# ---------------------------
# Online migrations
# ---------------------------
def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
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

# ---------------------------
# Run migrations
# ---------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
