from pathlib import Path

from alembic import command
from alembic.config import Config

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = BASE_DIR / "migrations"
SQL_MIGRATIONS_DIR = MIGRATIONS_DIR / "sql"
ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"


def get_alembic_config(database_url: str | None = None) -> Config:
    """Construct an Alembic Config object pointing to the workspace alembic.ini."""
    cfg = Config(str(ALEMBIC_INI_PATH))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def run_alembic_upgrade(revision: str = "head", database_url: str | None = None) -> None:
    """Execute Alembic upgrade command to the target revision."""
    cfg = get_alembic_config(database_url=database_url)
    command.upgrade(cfg, revision)


def run_alembic_downgrade(revision: str = "base", database_url: str | None = None) -> None:
    """Execute Alembic downgrade command to the target revision."""
    cfg = get_alembic_config(database_url=database_url)
    command.downgrade(cfg, revision)


def get_sql_migration_path(filename: str) -> Path:
    """Return absolute path to a SQL migration file in migrations/sql/."""
    path = SQL_MIGRATIONS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Migration file not found at {path}")
    return path


def read_sql_migration(filename: str) -> str:
    """Read contents of a SQL migration file."""
    path = get_sql_migration_path(filename)
    return path.read_text(encoding="utf-8")
