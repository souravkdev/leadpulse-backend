from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {}
engine_kwargs: dict = {"echo": settings.DEBUG}

if is_sqlite:
    connect_args = {"check_same_thread": False}
else:
    # Serverless-friendly: no persistent connection pool (Vercel/Neon).
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

# Enable WAL mode for SQLite to allow concurrent reads during writes
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
