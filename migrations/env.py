import os
import logging
from logging.config import fileConfig

from alembic import context
from models import db  # Now this works because env.py is in root

# Alembic Config object
config = context.config

# Logging setup
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# Hardcoded database URL (replace with your desired URL)
DATABASE_URL = 'postgresql://postgres:postgres@postgres:5432/app_db'
config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Metadata from models
target_metadata = db.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"}
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = db.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
