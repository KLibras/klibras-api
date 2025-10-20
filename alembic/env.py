import asyncio
import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# ADD THIS TO LOAD YOUR .env FILE
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ADD YOUR MODEL'S METADATA OBJECT HERE
# for 'autogenerate' support
# import your Base from wherever you defined it
from app.models.user import Base  # <-- ADJUST THIS IMPORT PATH IF NEEDED
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = os.getenv("DATABASE_URL")  # <-- LOAD URL FROM .env
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Helper function to run the migrations."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Get the database URL from the environment variable
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set.")

    # Create an async engine
    connectable = create_async_engine(
        db_url,
        poolclass=pool.NullPool,
    )

    # Connect and run migrations
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    # Dispose of the engine
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Run the async migrations function
    asyncio.run(run_migrations_online())