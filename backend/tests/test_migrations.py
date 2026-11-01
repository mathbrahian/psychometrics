from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_migrations_create_and_drop_the_table(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))

    command.upgrade(config, "head")
    columns = {column["name"] for column in inspect(create_engine(url)).get_columns("questionnaires")}
    assert columns == {"id", "title", "language", "total_items", "provider", "source_filename", "content", "created_at"}

    command.downgrade(config, "base")
    assert "questionnaires" not in inspect(create_engine(url)).get_table_names()
