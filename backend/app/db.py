from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Base de los modelos de SQLAlchemy. Alembic genera las migraciones a partir de su metadata."""


@lru_cache
def get_engine() -> Engine:
    """Un solo pool de conexiones por proceso. Se crea al primer uso, no al arrancar."""
    # pool_pre_ping descarta conexiones cortadas, por ejemplo después de reiniciar Cloud SQL.
    return create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=2)


def get_session() -> Iterator[Session]:
    session = sessionmaker(bind=get_engine(), expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
