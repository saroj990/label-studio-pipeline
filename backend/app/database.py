from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def apply_sqlite_migrations() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if not inspector.has_table("projects"):
        return
    columns = {col["name"] for col in inspector.get_columns("projects")}
    if "active_training_run_id" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE projects "
                    "ADD COLUMN active_training_run_id INTEGER"
                )
            )
