# File: carchive2/database/engine.py

from sqlalchemy import create_engine
from carchive.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, future=True)
