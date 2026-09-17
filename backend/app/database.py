"""SQLAlchemy engine/session wiring."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

connect_args = (
    {"check_same_thread": False} if settings.pavhan_db_url.startswith("sqlite") else {}
)
engine = create_engine(settings.pavhan_db_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sync_columns(base: type[DeclarativeBase]) -> list[str]:
    """Add columns the models have and the existing database does not.

    `create_all` creates missing *tables* and silently ignores missing
    *columns*, which is fine on a fresh clone and actively hostile to anyone
    who already ran an earlier version: their `pavhan.db` still has the old
    shape, and the first query against a new field fails with a bare
    "no such column" that reads like a code bug.

    This is not a migration framework and does not pretend to be one — it only
    adds, never alters or drops, because adding is the only change that cannot
    lose an artisan's data. Anything more than that belongs in Alembic, and
    would arrive with the same move to Postgres.
    """
    from sqlalchemy import inspect, text

    added: list[str] = []
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in base.metadata.sorted_tables:
            if table.name not in tables:
                continue  # create_all will make it in full
            have = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in have:
                    continue
                ddl = column.type.compile(engine.dialect)
                default = ""
                if column.default is not None and getattr(column.default, "is_scalar", False):
                    value = column.default.arg
                    default = f" DEFAULT {value!r}" if isinstance(value, str) else \
                        f" DEFAULT {value}"
                conn.execute(text(
                    f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl}{default}'))
                added.append(f"{table.name}.{column.name}")
    return added
