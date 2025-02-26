# carchive/core/security.py

import keyring
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_url():
    db_host = os.getenv("DB_HOST", "localhost")
    db_user = os.getenv("DB_USER", "carchive_app")
    db_name = os.getenv("DB_NAME", "carchive_db")
    password = keyring.get_password("carchive_app", "db_password")
    if not password:
        password = os.getenv("DB_PASS", "")
    return f"postgresql://{db_user}:{password}@{db_host}/{db_name}"
