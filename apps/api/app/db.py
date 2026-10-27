from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables, then add any missing columns (dev-only auto-migration).

    SQLite's create_all won't alter existing tables, so additive model changes
    would otherwise 500 on insert. This keeps dev smooth; use Alembic for prod.
    """
    from . import models  # noqa: F401  (ensure models are registered)

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    _relax_nullable_columns()


def _relax_nullable_columns() -> None:
    """Make columns that became Optional in the model nullable in an existing DB.

    `create_all` + ADD COLUMN can't relax a NOT NULL on a pre-existing column.
    `IdentityAssessment.confidence` went from NOT NULL (default 0.0) to nullable
    (None = 'identity not checked'), so an old dev DB would reject the insert.
    SQLite can't ALTER a constraint in place, so rebuild the table preserving data.
    """
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "identity_assessment" not in set(insp.get_table_names()):
        return
    conf = next(
        (c for c in insp.get_columns("identity_assessment") if c["name"] == "confidence"),
        None,
    )
    if conf is None or conf.get("nullable", True):
        return  # already nullable (fresh DBs) — nothing to do

    cols = "id, business_id, confidence, decision, matched_company_number, summary, created_at"
    if engine.dialect.name == "sqlite":
        try:
            with engine.begin() as conn:
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                conn.execute(text(
                    "ALTER TABLE identity_assessment RENAME TO identity_assessment__old"
                ))
            Base.metadata.tables["identity_assessment"].create(bind=engine)
            with engine.begin() as conn:
                conn.execute(text(
                    f"INSERT INTO identity_assessment ({cols}) "
                    f"SELECT {cols} FROM identity_assessment__old"
                ))
                conn.execute(text("DROP TABLE identity_assessment__old"))
                conn.execute(text("PRAGMA foreign_keys=ON"))
        except Exception:  # noqa: BLE001  (best-effort dev migration)
            pass
    else:
        try:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE identity_assessment "
                    "ALTER COLUMN confidence DROP NOT NULL"
                ))
        except Exception:  # noqa: BLE001
            pass


def _add_missing_columns() -> None:
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                coltype = col.type.compile(dialect=engine.dialect)
                try:
                    conn.execute(text(
                        f"ALTER TABLE {table.name} ADD COLUMN {col.name} {coltype}"
                    ))
                except Exception:  # noqa: BLE001  (best-effort dev migration)
                    pass
