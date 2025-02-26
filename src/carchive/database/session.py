# carchive/src/carchive/database/session.py

import contextlib
from sqlalchemy.orm import sessionmaker
from carchive.database.engine import engine

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

@contextlib.contextmanager
def get_session():
    """
    Use as:
        with get_session() as session:
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
