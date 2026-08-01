import os
import sys
from logging.config import fileConfig

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.config import _normalized_database_url, CONFIG_BY_NAME  # noqa: E402
from app.extensions import Base, build_engine, ensure_schema  # noqa: E402
import app.models  # noqa: E402,F401 - registers every model on Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the same DATABASE_URL resolution/normalization as the running app,
# rather than a static value baked into alembic.ini.
config.set_main_option("sqlalchemy.url", _normalized_database_url())

# Same DB_SCHEMA the running app uses — when sharing a database with
# another app, this keeps every table (and the version-tracking table)
# in a dedicated schema instead of colliding with 'public'.
db_schema = CONFIG_BY_NAME[os.environ.get("FLASK_ENV", "development")].DB_SCHEMA

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="galactic_builders_alembic_version",
        version_table_schema=db_schema,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = build_engine(config.get_main_option("sqlalchemy.url"), db_schema)
    ensure_schema(connectable, db_schema)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="galactic_builders_alembic_version",
            version_table_schema=db_schema,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
