import os
from logging.config import fileConfig
import sys
from sqlalchemy import create_engine
from alembic import context
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import db  # Your SQLAlchemy instance with metadata

# Alembic Config object
config = context.config

# Logging setup
fileConfig(config.config_file_name)
logger = config.get_section(config.config_file_name)

# ---------------- Hardcoded database URL ----------------
DATABASE_URL = 'postgresql://postgres:postgres@postgres:5432/app_db'
config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Target metadata from your models
target_metadata = db.metadata

# ---------------- Offline migrations ----------------
def run_migrations_offline():
    """Run migrations in 'offline' mode (just SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------- Online migrations ----------------
def run_migrations_online():
    """Run migrations in 'online' mode using SQLAlchemy engine."""
    connectable = create_engine(DATABASE_URL)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


# ---------------- Runner ----------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
