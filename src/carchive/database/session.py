# carchive/src/carchive/database/session.py

import contextlib
import functools
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

def db_session(func):
    """
    Decorator to provide a session to the wrapped function.
    The session is automatically closed after the function returns.
    
    Use as:
        @db_session
        def my_function(session, *args, **kwargs):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with get_session() as session:
            return func(session, *args, **kwargs)
    return wrapper
