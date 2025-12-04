import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import your models directly from root
from models import db  # db = SQLAlchemy() instance from models.py

# Alembic Config object
config = context.config

# Logging
fileConfig(config.config_file_name)

# Use DATABASE_URL from env or fallback to hardcoded
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://damko:damko@bee_db:5432/lab2"
)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Alembic target metadata for autogenerate
target_metadata = db.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
