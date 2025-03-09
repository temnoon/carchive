# File: carchive/database/engine.py

from sqlalchemy import create_engine
from carchive.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, future=True)

# Function to get the SQLAlchemy engine instance
def get_engine():
    """Return the SQLAlchemy engine instance."""
    return engine
