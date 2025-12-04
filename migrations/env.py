import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from models import db  # Your SQLAlchemy instance

# Alembic config
config = context.config
fileConfig(config.config_file_name)

# Hardcoded database URL (replace with your CI one if needed)
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://damko:damko@bee_db:5432/lab2"
config.set_main_option("sqlalchemy.url", DATABASE_URL)

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
        prefix='sqlalchemy.',
        poolclass=pool.NullPool
    )

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
